import logging
import os
import uuid
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

import config
import models
import schemas
import payment_gateway
import order_service
from database import get_db
from auth_utils import get_current_user
from routers.orders import order_out

logger = logging.getLogger("maumart.checkout")

router = APIRouter(prefix="/cart", tags=["cart"])

DELIVERY_FEE_FLAT = 500.0  # naira, flat per-vendor delivery fee for the demo
APP_URL = os.environ.get("MAUMART_APP_URL", "http://127.0.0.1:8551")


@router.post("/checkout", response_model=list[schemas.OrderOut])
def checkout(
    payload: schemas.CheckoutRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """
    Implements Section 7.3, with the corrected ordering (assessment P0-1):

      validate -> RESERVE STOCK ATOMICALLY -> create pending orders (commit)
      -> charge -> confirm | leave pending (live gateway) | release reservation.

    Stock is reserved before any money is requested, so two buyers can never both
    be charged for the last unit. With a live gateway the response carries
    status "pending_payment" and a payment_url; the orders are confirmed later by the
    signed webhook or POST /payments/verify/{reference}.
    """
    if not payload.items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    if config.is_production() and payment_gateway.is_mock() and payload.payment_method != "pay_on_delivery":
        # Pilot mode (MAUMART_PILOT_COD_ONLY): the mock gateway would "approve" this without taking money.
        raise HTTPException(status_code=400, detail="Only pay on delivery is available right now")

    # Merge duplicate lines: two cart lines for one listing must be checked as one quantity.
    wanted: dict[str, int] = defaultdict(int)
    for item in payload.items:
        wanted[item.listing_id] += item.quantity

    # Step 1: friendly pre-check (the atomic reservation below is the authoritative one).
    listings_by_id = {
        l.id: l for l in db.query(models.Listing).filter(models.Listing.id.in_(list(wanted))).all()
    }
    for listing_id, qty in wanted.items():
        listing = listings_by_id.get(listing_id)
        if not listing or listing.status != "live":
            raise HTTPException(status_code=400, detail=f"Item unavailable: {listing_id}")
        if qty > listing.quantity:
            raise HTTPException(status_code=400, detail=f"Not enough stock for: {listing.title}")

    # Step 2: reserve stock atomically. Zero rows updated == someone else got there first.
    try:
        order_service.reserve_stock(db, dict(wanted))
    except order_service.InsufficientStock as exc:
        db.rollback()
        title = listings_by_id[exc.listing_id].title
        raise HTTPException(status_code=400, detail=f"Not enough stock for: {title}")

    # Step 3: group by vendor and create pending orders in the SAME transaction as the reservation.
    groups: dict[str, dict[str, int]] = defaultdict(dict)
    for listing_id, qty in wanted.items():
        groups[listings_by_id[listing_id].vendor_id][listing_id] = qty

    cod = payload.payment_method == "pay_on_delivery"
    # Only a live gateway leaves orders pending, so only then can a reservation need to expire.
    expires_at = None
    if not cod and not payment_gateway.is_mock():
        expires_at = datetime.utcnow() + timedelta(minutes=order_service.RESERVATION_MINUTES)

    session_id = str(uuid.uuid4())
    total_landed_cost = 0.0
    pending_orders: list[models.Order] = []

    for vendor_id, lines in groups.items():
        subtotal = round(sum(listings_by_id[lid].price * qty for lid, qty in lines.items()), 2)
        vat = round(subtotal * models.VAT_RATE, 2)
        group_total = round(subtotal + vat + DELIVERY_FEE_FLAT, 2)
        total_landed_cost += group_total

        order = models.Order(
            buyer_id=user.id, vendor_id=vendor_id, session_id=session_id,
            subtotal=subtotal, vat_amount=vat, delivery_fee=DELIVERY_FEE_FLAT, total=group_total,
            status="pending_payment", delivery_address=payload.delivery_address,
            expires_at=expires_at,
        )
        db.add(order)
        db.flush()
        for lid, qty in lines.items():
            db.add(models.OrderItem(
                order_id=order.id, listing_id=lid, quantity=qty,
                price_at_purchase=listings_by_id[lid].price,
            ))
        pending_orders.append(order)

    db.commit()  # reservation + pending orders are now durable
    order_ids = [o.id for o in pending_orders]
    total_landed_cost = round(total_landed_cost, 2)

    # Step 4: payment. Cash on delivery never touches the gateway (it would otherwise start a real
    # Paystack transaction in live mode); the others go through the configured gateway.
    if cod:
        result = {"status": "success", "reference": f"COD-{uuid.uuid4().hex[:10]}"}
    else:
        try:
            result = payment_gateway.charge(
                total_landed_cost, payload.payment_method, session_id,
                email=user.email, callback_url=APP_URL,
            )
        except Exception:  # a gateway outage must release the stock, not strand it
            logger.exception("gateway charge raised for session %s", session_id)
            result = {"status": "failed", "reference": None}

    if result["status"] == "success":
        confirmed = [oid for oid in order_ids if order_service.confirm_order(db, oid, result.get("reference"))]
        db.commit()
        order_service.notify_confirmed(db, confirmed)

    elif result["status"] == "pending":
        for oid in order_ids:
            order = db.get(models.Order, oid)
            order.payment_reference = result["reference"]
            order.payment_url = result.get("authorization_url")
        db.commit()

    else:
        for oid in order_ids:
            order_service.release_order(db, oid)
        db.commit()
        raise HTTPException(status_code=402, detail="Payment failed, please retry")

    orders = (
        db.query(models.Order).options(joinedload(models.Order.vendor))
        .filter(models.Order.id.in_(order_ids)).all()
    )
    return [order_out(o) for o in orders]
