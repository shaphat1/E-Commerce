from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

import models
import schemas
import notifications
import order_service
from database import get_db
from auth_utils import get_current_user, require_role

router = APIRouter(prefix="/orders", tags=["orders"])

MAX_ORDER_LIST = 200


def order_out(order: models.Order) -> schemas.OrderOut:
    """Single serializer used by checkout, payment verification and the order lists."""
    return schemas.OrderOut(
        id=order.id, vendor_id=order.vendor_id,
        vendor_name=order.vendor.business_name if order.vendor else None,
        buyer_id=order.buyer_id, session_id=order.session_id,
        subtotal=order.subtotal, vat_amount=order.vat_amount, delivery_fee=order.delivery_fee,
        total=order.total, status=order.status, delivery_address=order.delivery_address,
        created_at=order.created_at,
        payment_url=order.payment_url if order.status == "pending_payment" else None,
        payment_reference=order.payment_reference,
    )


@router.get("/mine", response_model=list[schemas.OrderOut])
def my_orders(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """FR-5.1 -- buyer order history (newest first)."""
    orders = (
        db.query(models.Order).options(joinedload(models.Order.vendor))
        .filter(models.Order.buyer_id == user.id)
        .order_by(models.Order.created_at.desc()).limit(MAX_ORDER_LIST).all()
    )
    return [order_out(o) for o in orders]


@router.get("/vendor/incoming", response_model=list[schemas.OrderOut])
def incoming_orders(db: Session = Depends(get_db), user: models.User = Depends(require_role("vendor"))):
    """FR-5.2 -- vendor's incoming orders, for their dashboard. Unpaid orders are not shown."""
    vendor = db.query(models.Vendor).filter(models.Vendor.user_id == user.id).first()
    orders = (
        db.query(models.Order).options(joinedload(models.Order.vendor))
        .filter(models.Order.vendor_id == vendor.id, models.Order.status != "pending_payment")
        .order_by(models.Order.created_at.desc()).limit(MAX_ORDER_LIST).all()
    )
    return [order_out(o) for o in orders]


@router.patch("/{order_id}/status", response_model=schemas.OrderOut)
def update_status(
    order_id: str,
    payload: schemas.OrderStatusUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role("vendor")),
):
    """Implements the order status update algorithm, Section 7.4."""
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.vendor.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    allowed_next = models.ORDER_STATUS_FLOW.get(order.status, [])
    if payload.new_status not in allowed_next:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot move from '{order.status}' to '{payload.new_status}'. Allowed: {allowed_next}",
        )
    # pending_payment -> confirmed_paid/payment_failed is the payment system's decision
    # (webhook / verify / expiry), never a vendor's: otherwise a vendor could mark an unpaid order paid.
    if order.status == "pending_payment":
        raise HTTPException(status_code=400, detail="This order is awaiting payment")

    order.status = payload.new_status
    db.commit()
    db.refresh(order)
    notifications.notify_order_status_changed(order.buyer.email, order.id, order.status)
    return order_out(order)


@router.post("/{order_id}/cancel", response_model=schemas.OrderOut)
def cancel_order(order_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """FR-5.3 -- buyer can only cancel while status is still pending_payment; the reserved stock is returned."""
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order or order.buyer_id != user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    if not order_service.release_order(db, order.id):
        raise HTTPException(status_code=400, detail="Order already confirmed -- raise a dispute instead")
    db.commit()
    db.refresh(order)
    return order_out(order)


@router.post("/disputes")
def raise_dispute(
    payload: schemas.DisputeCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """FR-5.4 -- buyer flags a PAID order; lands in the admin queue (one open dispute per order)."""
    order = db.query(models.Order).filter(models.Order.id == payload.order_id).first()
    if not order or order.buyer_id != user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status not in models.PAID_STATUSES:
        raise HTTPException(status_code=400, detail="Only paid orders can be disputed")
    already_open = db.query(models.Dispute.id).filter(
        models.Dispute.order_id == order.id, models.Dispute.status == "open"
    ).first()
    if already_open:
        raise HTTPException(status_code=400, detail="A dispute is already open for this order")
    dispute = models.Dispute(order_id=order.id, buyer_id=user.id, reason=payload.reason, status="open")
    db.add(dispute)
    db.commit()
    db.refresh(dispute)
    return {"id": dispute.id, "status": dispute.status}
