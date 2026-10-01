"""
Payment confirmation for the live (Paystack) gateway.

  POST /payments/webhook/paystack   Paystack -> us. Signature-verified, idempotent.
  POST /payments/verify/{reference} Buyer's app -> us. Asks Paystack directly; covers a
                                    delayed or lost webhook.

Both end in order_service.settle_paid_session(), so a replayed webhook, a webhook plus a
manual verify, or a retry storm all change nothing the second time.

With the mock gateway these routes answer 404: there is nothing to confirm.
"""
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session, joinedload

import models
import schemas
import payment_gateway
import order_service
from database import SessionLocal, get_db
from auth_utils import get_current_user
from rate_limit import rate_limit
from routers.orders import order_out

logger = logging.getLogger("maumart.payments")

router = APIRouter(prefix="/payments", tags=["payments"])


def _process_webhook(event: dict) -> dict:
    """Runs in a worker thread with its own DB session (the request body had to be read async)."""
    if event.get("event") != "charge.success":
        return {"received": True, "ignored": event.get("event")}
    data = event.get("data") or {}
    reference = data.get("reference")
    if not reference or data.get("status") != "success":
        return {"received": True, "ignored": "not a successful charge"}

    db = SessionLocal()
    try:
        result = order_service.settle_paid_session(db, reference, data.get("amount"), data.get("currency"))
        order_service.notify_confirmed(db, result["confirmed"])
    finally:
        db.close()
    if not result["found"]:
        logger.warning("webhook for unknown reference %s", reference)
    return {"received": True, "confirmed": len(result["confirmed"]), "amount_mismatch": result["amount_mismatch"]}


@router.post("/webhook/paystack")
async def paystack_webhook(request: Request):
    if payment_gateway.is_mock():
        raise HTTPException(status_code=404, detail="Not found")

    raw = await request.body()  # the signature is over the exact bytes, so verify before parsing
    signature = request.headers.get("x-paystack-signature", "")
    if not payment_gateway.verify_webhook_signature(raw, signature, payment_gateway.webhook_secret()):
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        event = json.loads(raw)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    return await run_in_threadpool(_process_webhook, event)


@router.post("/verify/{reference}", response_model=list[schemas.OrderOut],
             dependencies=[Depends(rate_limit(30, 60))])
def verify_payment(reference: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """The buyer's 'I've paid' button: ask the gateway, then confirm. Safe to call repeatedly."""
    if payment_gateway.is_mock():
        raise HTTPException(status_code=404, detail="Not found")

    owned = db.query(models.Order).filter(
        models.Order.payment_reference == reference, models.Order.buyer_id == user.id
    ).first()
    if not owned:
        raise HTTPException(status_code=404, detail="Payment not found")

    check = payment_gateway.verify(reference)
    if check["status"] == "success":
        result = order_service.settle_paid_session(db, reference, check.get("amount_kobo"), check.get("currency"))
        order_service.notify_confirmed(db, result["confirmed"])
    elif check["status"] == "error":
        raise HTTPException(status_code=502, detail="Could not reach the payment provider, try again shortly")

    orders = (
        db.query(models.Order).options(joinedload(models.Order.vendor))
        .filter(models.Order.payment_reference == reference, models.Order.buyer_id == user.id).all()
    )
    return [order_out(o) for o in orders]
