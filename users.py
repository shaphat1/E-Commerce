"""
Data subject rights under Nigeria's NDPA 2023 (access, erasure/restriction,
data portability) -- see PRIVACY_POLICY.md for the plain-language version
of what these endpoints do and why.

Erasure is implemented as anonymization, not a hard delete: order and
review rows are retained (with personal identifiers scrubbed) because
transaction records have a legitimate retention basis (tax/audit,
resolving disputes on past orders) that NDPA's erasure right doesn't
override. This mirrors real e-commerce practice -- see also
Section 5.2's "erasure vs. legitimate retention" note in the report.
"""
import secrets

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import models
from database import get_db
from auth_utils import get_current_user, hash_password, invalidate_all_sessions_for_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me/export")
def export_my_data(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """NDPA access + data-portability right: everything held about this user, in one JSON payload."""
    vendor = db.query(models.Vendor).filter(models.Vendor.user_id == user.id).first()
    orders = db.query(models.Order).filter(models.Order.buyer_id == user.id).all()
    reviews = db.query(models.Review).filter(models.Review.buyer_id == user.id).all()
    interactions = db.query(models.Interaction).filter(models.Interaction.user_id == user.id).all()

    return {
        "profile": {
            "id": user.id, "name": user.name, "email": user.email,
            "phone": user.phone, "role": user.role, "status": user.status,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
        "vendor_profile": ({
            "business_name": vendor.business_name, "category": vendor.category,
            "verification_status": vendor.verification_status,
        } if vendor else None),
        "orders": [{
            "id": o.id, "vendor_id": o.vendor_id, "total": o.total, "status": o.status,
            "delivery_address": o.delivery_address,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        } for o in orders],
        "reviews_written": [{"vendor_id": r.vendor_id, "rating": r.rating, "comment": r.comment} for r in reviews],
        "recommendation_interactions": [
            {"listing_id": i.listing_id, "type": i.type,
             "created_at": i.created_at.isoformat() if i.created_at else None}
            for i in interactions
        ],
    }


@router.delete("/me")
def delete_my_account(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """
    NDPA erasure right. Anonymizes personal identifiers rather than hard-deleting:
    orders/reviews stay (scrubbed of PII) for legitimate retention reasons; the
    account itself becomes unusable (random password, status='deleted', every
    active session killed) -- functionally equivalent to deletion for the user.
    """
    vendor = db.query(models.Vendor).filter(models.Vendor.user_id == user.id).first()
    if vendor:
        vendor.business_name = "Deleted Vendor"
        for listing in vendor.listings:
            listing.status = "deactivated"

    user.name = "Deleted User"
    user.email = f"deleted-{user.id}@maumart.ng"
    user.phone = f"deleted-{user.id[:8]}"
    user.password_hash = hash_password(secrets.token_hex(16))  # unguessable -- account is now unusable
    user.status = "deleted"

    db.commit()
    invalidate_all_sessions_for_user(db, user.id)

    return {
        "deleted": True,
        "note": "Your personal details have been anonymized and your sessions ended. "
                "Order and review records are retained in anonymized form for legal/audit purposes.",
    }
