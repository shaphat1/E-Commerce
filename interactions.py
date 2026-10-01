from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

import models
from database import get_db
from auth_utils import get_current_user

router = APIRouter(prefix="/interactions", tags=["interactions"])


@router.post("/view/{listing_id}")
def log_view(listing_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """Called by the client when a buyer opens a product detail page (FR-7.2/7.3 signal)."""
    if not db.query(models.Listing.id).filter(models.Listing.id == listing_id).first():
        raise HTTPException(status_code=404, detail="Listing not found")  # was a foreign-key 500 on Postgres
    db.add(models.Interaction(user_id=user.id, listing_id=listing_id, type="view"))
    db.commit()
    return {"logged": True}


@router.get("/mine")
def my_interactions(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """FR-7.5 -- lets a buyer see exactly what's feeding their recommendations."""
    interactions = (
        db.query(models.Interaction).options(joinedload(models.Interaction.listing))
        .filter(models.Interaction.user_id == user.id)
        .order_by(models.Interaction.created_at.desc()).limit(500).all()
    )
    return [
        {
            "listing_id": i.listing_id,
            "listing_title": i.listing.title if i.listing else "(listing removed)",
            "type": i.type,
            "created_at": i.created_at.isoformat() if i.created_at else None,
        }
        for i in interactions
    ]


@router.delete("/mine")
def clear_my_interactions(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """
    FR-7.5 -- clears the recommendation signal only. Deliberately does NOT touch
    Orders/OrderItems: this is a data-minimisation control over personalization,
    not an erasure of transaction records (those have their own retention basis,
    see routers/users.py).
    """
    deleted = db.query(models.Interaction).filter(models.Interaction.user_id == user.id).delete()
    db.commit()
    return {"cleared": deleted}
