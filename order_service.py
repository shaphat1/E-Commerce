"""
Stock reservation and order payment-state transitions.

Why this module exists (assessment item P0-1): checkout used to read the stock,
charge the buyer, and only afterwards decrement the stock in a separate
statement, so concurrent buyers of the last unit were all charged. The rules now are:

  1. STOCK IS RESERVED FIRST, ATOMICALLY, BEFORE ANY CHARGE.
     `UPDATE listings SET quantity = quantity - n WHERE id = :id AND quantity >= n`
     -- zero rows updated means "not enough stock". The database serialises
     concurrent updates of one row, so two buyers can never both take the last unit.
  2. Every state change is a conditional UPDATE (`... WHERE status = 'pending_payment'`)
     whose row count says whether THIS call made the change. That makes confirm and
     release idempotent: a replayed webhook, a double click and the expiry sweeper
     racing each other cannot double-count stock or double-confirm an order.
  3. A reservation that is never paid for lapses (expires_at) and the sweeper returns
     the stock -- but first asks the gateway whether the buyer actually paid.
  4. If money arrives for an order whose reservation was already released, we try to
     re-reserve; if the stock is gone, an admin dispute is opened so the buyer is refunded.

Callers own the transaction boundary (commit/rollback) unless noted.
"""
import logging
import os
from datetime import datetime

from sqlalchemy import update, func
from sqlalchemy.orm import Session, joinedload

import models
import notifications
import payment_gateway

logger = logging.getLogger("maumart.orders")

RESERVATION_MINUTES = int(os.environ.get("MAUMART_RESERVATION_MINUTES", "30"))

_NO_SYNC = {"synchronize_session": False}


class InsufficientStock(Exception):
    def __init__(self, listing_id: str):
        self.listing_id = listing_id
        super().__init__(f"insufficient stock for listing {listing_id}")


def _now() -> datetime:
    return datetime.utcnow()


def reserve_stock(db: Session, lines: dict[str, int]) -> None:
    """
    Atomically take `quantity` units of each listing, or raise InsufficientStock.
    Caller must roll back on failure so units taken earlier in the loop are returned.
    Listings are locked in sorted-id order so two checkouts touching the same pair of
    listings can never deadlock each other.
    """
    for listing_id in sorted(lines):
        qty = lines[listing_id]
        result = db.execute(
            update(models.Listing)
            .where(
                models.Listing.id == listing_id,
                models.Listing.status == "live",
                models.Listing.quantity >= qty,
            )
            .values(quantity=models.Listing.quantity - qty),
            execution_options=_NO_SYNC,
        )
        if result.rowcount != 1:
            raise InsufficientStock(listing_id)


def _return_stock(db: Session, order_id: str) -> None:
    items = db.query(models.OrderItem.listing_id, models.OrderItem.quantity).filter(
        models.OrderItem.order_id == order_id
    ).order_by(models.OrderItem.listing_id).all()
    for listing_id, qty in items:
        db.execute(
            update(models.Listing).where(models.Listing.id == listing_id)
            .values(quantity=models.Listing.quantity + qty),
            execution_options=_NO_SYNC,
        )


def release_order(db: Session, order_id: str) -> bool:
    """
    pending_payment -> payment_failed, giving the reserved stock back.
    Returns False (and does nothing) if the order was no longer pending, so it is
    safe to call from checkout failure, buyer cancel and the expiry sweeper alike.
    """
    result = db.execute(
        update(models.Order)
        .where(models.Order.id == order_id, models.Order.status == "pending_payment")
        .values(status="payment_failed", expires_at=None, payment_url=None, updated_at=_now()),
        execution_options=_NO_SYNC,
    )
    if result.rowcount != 1:
        return False
    _return_stock(db, order_id)
    return True


def _record_purchase(db: Session, order_id: str) -> None:
    buyer_id = db.query(models.Order.buyer_id).filter(models.Order.id == order_id).scalar()
    items = db.query(models.OrderItem.listing_id, models.OrderItem.quantity).filter(
        models.OrderItem.order_id == order_id
    ).order_by(models.OrderItem.listing_id).all()
    for listing_id, qty in items:
        db.execute(
            update(models.Listing).where(models.Listing.id == listing_id)
            .values(sales_count=func.coalesce(models.Listing.sales_count, 0) + qty),
            execution_options=_NO_SYNC,
        )
        db.add(models.Interaction(user_id=buyer_id, listing_id=listing_id, type="purchase"))


def confirm_order(db: Session, order_id: str, reference: str | None = None) -> bool:
    """
    pending_payment -> confirmed_paid. Stock was already reserved at checkout, so only
    sales counters and the purchase signal are written here. Returns False if the order
    was not pending (already confirmed, released, ...): replays are harmless no-ops.
    """
    values = {"status": "confirmed_paid", "expires_at": None, "payment_url": None, "updated_at": _now()}
    if reference:
        values["payment_reference"] = reference
    result = db.execute(
        update(models.Order)
        .where(models.Order.id == order_id, models.Order.status == "pending_payment")
        .values(**values),
        execution_options=_NO_SYNC,
    )
    if result.rowcount != 1:
        return False
    _record_purchase(db, order_id)
    return True


def _open_refund_dispute(db: Session, order_id: str, buyer_id: str) -> None:
    exists = db.query(models.Dispute.id).filter(
        models.Dispute.order_id == order_id, models.Dispute.status == "open"
    ).first()
    if not exists:
        db.add(models.Dispute(
            order_id=order_id, buyer_id=buyer_id, status="open",
            reason=("AUTO: payment was received after this order's stock reservation had been "
                    "released and the item is no longer available. Refund the buyer."),
        ))
    db.commit()


def recover_late_payment(db: Session, order: models.Order) -> str:
    """
    Money arrived for an order already released to payment_failed (reservation expired or
    buyer cancelled after paying). Re-reserve and honour the order if stock allows;
    otherwise queue a refund. Commits/rolls back itself. Returns recovered|needs_refund|skipped.
    """
    order_id, buyer_id = order.id, order.buyer_id
    lines: dict[str, int] = {}
    for it in order.items:
        lines[it.listing_id] = lines.get(it.listing_id, 0) + it.quantity
    try:
        reserve_stock(db, lines)
    except InsufficientStock:
        db.rollback()
        _open_refund_dispute(db, order_id, buyer_id)
        logger.error("late payment for order %s but stock gone -- refund dispute opened", order_id)
        return "needs_refund"
    result = db.execute(
        update(models.Order)
        .where(models.Order.id == order_id, models.Order.status == "payment_failed")
        .values(status="confirmed_paid", expires_at=None, payment_url=None, updated_at=_now()),
        execution_options=_NO_SYNC,
    )
    if result.rowcount != 1:
        db.rollback()  # someone else changed it meanwhile; this also undoes the re-reservation
        return "skipped"
    _record_purchase(db, order_id)
    db.commit()
    return "recovered"


def settle_paid_session(db: Session, reference: str, amount_kobo: int | None = None,
                        currency: str | None = None) -> dict:
    """
    The gateway says `reference` was paid. Confirm every order in that checkout session.
    Idempotent. If an amount is supplied it MUST equal the session total -- a signed webhook
    for the wrong amount is logged and ignored rather than trusted.
    Returns {"found", "amount_mismatch", "confirmed": [ids], "needs_refund": [ids]}.
    """
    out = {"found": False, "amount_mismatch": False, "confirmed": [], "needs_refund": []}
    orders = db.query(models.Order).filter(models.Order.payment_reference == reference).all()
    if not orders:
        return out
    out["found"] = True

    expected = payment_gateway.to_kobo(sum(o.total for o in orders))
    if (amount_kobo is not None and amount_kobo != expected) or (currency not in (None, "NGN")):
        logger.error("payment mismatch reference=%s expected_kobo=%s got_kobo=%s currency=%s",
                     reference, expected, amount_kobo, currency)
        out["amount_mismatch"] = True
        return out

    pending = [(o.id, o.status) for o in orders]
    for order_id, status in pending:
        if status == "pending_payment":
            if confirm_order(db, order_id, reference):
                out["confirmed"].append(order_id)
            db.commit()
        elif status == "payment_failed":
            order = db.query(models.Order).filter(models.Order.id == order_id).first()
            outcome = recover_late_payment(db, order)
            if outcome == "recovered":
                out["confirmed"].append(order_id)
            elif outcome == "needs_refund":
                out["needs_refund"].append(order_id)
        # any other status: already paid/progressed -- nothing to do (idempotent replay)
    return out


def notify_confirmed(db: Session, order_ids: list[str]) -> None:
    """Send the 'order placed' emails. Call only after the confirming transaction committed."""
    if not order_ids:
        return
    orders = (
        db.query(models.Order)
        .options(joinedload(models.Order.buyer), joinedload(models.Order.vendor).joinedload(models.Vendor.user))
        .filter(models.Order.id.in_(order_ids)).all()
    )
    for o in orders:
        notifications.notify_order_placed(o.buyer.email, o.id, o.total, o.vendor.business_name)
        notifications.notify_vendor_new_order(o.vendor.user.email, o.id, o.total)


def expire_stale_reservations(db: Session) -> int:
    """
    Release pending orders whose reservation lapsed, returning stock to the shelf.
    With a live gateway each reference is first checked with Paystack: if the buyer did pay
    (webhook delayed or lost) the order is confirmed instead of released. If Paystack cannot
    be reached we leave the order alone and retry on the next sweep. Returns orders released.
    """
    stale = db.query(models.Order.id, models.Order.payment_reference).filter(
        models.Order.status == "pending_payment",
        models.Order.expires_at.isnot(None),
        models.Order.expires_at < _now(),
    ).limit(500).all()

    by_ref: dict[str | None, list[str]] = {}
    for order_id, ref in stale:
        by_ref.setdefault(ref, []).append(order_id)

    released = 0
    for ref, ids in by_ref.items():
        if ref and not payment_gateway.is_mock():
            check = payment_gateway.verify(ref)
            if check["status"] == "success":
                result = settle_paid_session(db, ref, check.get("amount_kobo"), check.get("currency"))
                notify_confirmed(db, result["confirmed"])
                continue
            if check["status"] == "error":
                continue
        for order_id in ids:
            if release_order(db, order_id):
                released += 1
        db.commit()
    return released
