from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from auth_utils import get_current_user

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post("")
def create_review(
    payload: schemas.ReviewCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """FR-6.1/6.3 -- only the buyer of a *completed* order can review it, once."""
    order = db.query(models.Order).filter(models.Order.id == payload.order_id).first()
    if not order or order.buyer_id != user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != "completed":
        raise HTTPException(status_code=400, detail="Reviews unlock once the order is completed")

    existing = db.query(models.Review).filter(models.Review.order_id == order.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="You already reviewed this order")

    review = models.Review(
        order_id=order.id, buyer_id=user.id, vendor_id=order.vendor_id,
        rating=payload.rating, comment=payload.comment,
    )
    db.add(review)
    try:
        db.commit()
    except IntegrityError:  # two simultaneous submits: the unique constraint on order_id decides
        db.rollback()
        raise HTTPException(status_code=400, detail="You already reviewed this order")
    db.refresh(review)
    return {"id": review.id, "rating": review.rating}


@router.get("/vendor/{vendor_id}")
def vendor_reviews(vendor_id: str, db: Session = Depends(get_db)):
    """FR-6.2 -- aggregate rating + review list for a vendor's public profile."""
    reviews = db.query(models.Review).filter(models.Review.vendor_id == vendor_id).all()
    if not reviews:
        return {"average_rating": None, "count": 0, "reviews": []}
    avg = sum(r.rating for r in reviews) / len(reviews)
    return {
        "average_rating": round(avg, 2),
        "count": len(reviews),
        "reviews": [{"rating": r.rating, "comment": r.comment} for r in reviews],
    }
