from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

import models
import schemas
import payment_gateway
import notifications
from database import get_db
from auth_utils import require_role

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/vendors/pending")
def pending_vendors(db: Session = Depends(get_db), _admin=Depends(require_role("admin"))):
    vendors = db.query(models.Vendor).filter(models.Vendor.verification_status == "pending").all()
    return [{"id": v.id, "business_name": v.business_name, "category": v.category} for v in vendors]


@router.post("/vendors/{vendor_id}/approve")
def approve_vendor(vendor_id: str, db: Session = Depends(get_db), _admin=Depends(require_role("admin"))):
    """FR-8.1 -- unblocks the vendor (FR-1.4) so they can create listings (FR-2.1)."""
    vendor = db.query(models.Vendor).filter(models.Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    vendor.verification_status = "approved"
    vendor.user.status = "active"
    db.commit()
    return {"id": vendor.id, "verification_status": vendor.verification_status}


@router.get("/listings/pending")
def pending_listings(db: Session = Depends(get_db), _admin=Depends(require_role("admin"))):
    listings = db.query(models.Listing).options(joinedload(models.Listing.vendor)).filter(
        models.Listing.status == "pending_admin_review").all()
    return [{"id": l.id, "title": l.title, "category": l.category, "vendor": l.vendor.business_name} for l in listings]


@router.post("/listings/{listing_id}/approve")
def approve_listing(listing_id: str, db: Session = Depends(get_db), _admin=Depends(require_role("admin"))):
    listing = db.query(models.Listing).filter(models.Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    listing.status = "live"
    db.commit()
    return {"id": listing.id, "status": listing.status}


@router.get("/disputes")
def open_disputes(db: Session = Depends(get_db), _admin=Depends(require_role("admin"))):
    """FR-8.2 -- disputes escalated from FR-5.4."""
    disputes = db.query(models.Dispute).filter(models.Dispute.status == "open").all()
    return [{"id": d.id, "order_id": d.order_id, "reason": d.reason} for d in disputes]


@router.post("/disputes/{dispute_id}/resolve")
def resolve_dispute(
    dispute_id: str,
    payload: schemas.DisputeResolution,
    db: Session = Depends(get_db),
    _admin=Depends(require_role("admin")),
):
    """
    Implements the Refund & Return Policy (REFUND_POLICY.md Section 3):
    an admin resolves a dispute either with no refund, or by actually
    reversing the payment through the gateway and marking the order
    'refunded' -- not just flipping a status label.
    """
    dispute = db.query(models.Dispute).filter(models.Dispute.id == dispute_id).first()
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    if dispute.status != "open":
        # Without this, resolving twice would refund the buyer twice.
        raise HTTPException(status_code=400, detail=f"Dispute is already {dispute.status}")

    order = db.query(models.Order).filter(models.Order.id == dispute.order_id).first()

    if payload.refund:
        if order.status == "refunded":
            raise HTTPException(status_code=400, detail="Order is already refunded")
        if not order.payment_reference:
            raise HTTPException(status_code=400, detail="Order has no payment reference to refund")
        if order.payment_reference.startswith("COD-"):
            # Cash on delivery: no card/bank money passed through the gateway, so there is nothing to
            # reverse there. The refund of any cash handed over is arranged offline with the vendor.
            pass
        else:
            result = payment_gateway.refund(order.payment_reference, order.total)
            if result["status"] != "success":
                raise HTTPException(status_code=502, detail=f"Refund failed at gateway: {result.get('reason')}")
        order.status = "refunded"
        dispute.status = "refunded"
        db.commit()
        notifications.notify_order_refunded(order.buyer.email, order.id, order.total)
    else:
        dispute.status = "resolved_no_refund"
        db.commit()

    return {"id": dispute.id, "status": dispute.status, "order_status": order.status}


@router.get("/stats")
def platform_stats(db: Session = Depends(get_db), _admin=Depends(require_role("admin"))):
    """FR-8.3 -- lightweight platform analytics."""
    # Sum in SQL over every paid status (not just "confirmed_paid", which orders leave as they progress).
    total_gmv = db.query(func.coalesce(func.sum(models.Order.total), 0.0)).filter(
        models.Order.status.in_(models.PAID_STATUSES)).scalar()
    return {
        "active_vendors": db.query(models.Vendor).filter(models.Vendor.verification_status == "approved").count(),
        "active_buyers": db.query(models.User).filter(models.User.role == "buyer").count(),
        "live_listings": db.query(models.Listing).filter(models.Listing.status == "live").count(),
        "gmv": round(float(total_gmv), 2),
    }
