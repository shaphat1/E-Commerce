from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import or_, func

import models
import schemas
from database import get_db, engine
from auth_utils import require_role

router = APIRouter(prefix="/listings", tags=["listings"])

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100


def with_relations(query):
    """
    Eager-load what _to_out() touches (vendor, photos) in 2 extra queries total, instead of
    2 lazy queries PER listing -- browsing 500 listings used to issue 507 SQL queries.
    """
    return query.options(joinedload(models.Listing.vendor), selectinload(models.Listing.photos))


def like_pattern(q: str) -> str:
    """Escape LIKE wildcards so a search for '100%' or 'a_b' matches literally."""
    return "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def _to_out(listing: models.Listing, reason: str = None) -> schemas.ListingOut:
    vendor = listing.vendor
    return schemas.ListingOut(
        id=listing.id,
        vendor_id=vendor.id,
        vendor_name=vendor.business_name,
        title=listing.title,
        category=listing.category,
        description=listing.description,
        price=listing.price,
        quantity=listing.quantity,
        status=listing.status,
        photo_urls=[p.url for p in listing.photos],
        reason=reason,
    )


@router.post("", response_model=schemas.ListingOut)
def create_listing(
    payload: schemas.ListingCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role("vendor")),
):
    """Implements the vendor listing creation algorithm, Section 7.2."""
    vendor = db.query(models.Vendor).filter(models.Vendor.user_id == user.id).first()
    if not vendor or vendor.verification_status != "approved":
        raise HTTPException(status_code=403, detail="Complete vendor verification first")

    status_value = "live"
    if payload.category in models.RESTRICTED_CATEGORIES:
        # Coursework-scope simplification of FR-2.4's whitelist check: restricted
        # categories always require admin sign-off rather than auto-publishing.
        status_value = "pending_admin_review"

    listing = models.Listing(
        vendor_id=vendor.id,
        title=payload.title,
        category=payload.category,
        description=payload.description,
        price=payload.price,
        quantity=payload.quantity,
        delivery_options=payload.delivery_options,
        status=status_value,
    )
    db.add(listing)
    db.flush()
    for url in payload.photo_urls:
        db.add(models.ListingPhoto(listing_id=listing.id, url=url))
    db.commit()
    db.refresh(listing)
    return _to_out(listing)


@router.get("", response_model=list[schemas.ListingOut])
def browse_listings(
    response: Response,
    category: Optional[str] = None,
    q: Optional[str] = Query(default=None, max_length=100, description="Search keyword"),
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """
    FR-3.1/3.2 -- category browse, keyword search, price filter. Only live listings.

    Search dialect note: on Postgres this uses real full-text search
    (to_tsvector/plainto_tsquery, ranked by relevance) rather than a plain
    LIKE scan -- the closest honest equivalent to the Elasticsearch/OpenSearch
    named in the report's Section 8.2 that's actually reachable from this
    environment (elastic.co isn't a network-allowed domain here). SQLite falls
    back to ILIKE, which is what the original coursework build used throughout.

    Paginated: `limit` (default 50, max 100) and `offset`; the total number of matches is returned
    in the X-Total-Count header. Previously this returned every live listing in one response.
    """
    query = db.query(models.Listing).filter(models.Listing.status == "live")
    if category:
        query = query.filter(models.Listing.category == category)

    rank = None
    if q:
        if engine.dialect.name == "postgresql":
            ts_query = func.plainto_tsquery("english", q)
            ts_doc = func.to_tsvector("english", models.Listing.title + " " + func.coalesce(models.Listing.description, ""))
            query = query.filter(ts_doc.op("@@")(ts_query))
            rank = func.ts_rank(ts_doc, ts_query).desc()
        else:
            like = like_pattern(q)
            query = query.filter(or_(
                models.Listing.title.ilike(like, escape="\\"),
                models.Listing.description.ilike(like, escape="\\"),
            ))

    if min_price is not None:
        query = query.filter(models.Listing.price >= min_price)
    if max_price is not None:
        query = query.filter(models.Listing.price <= max_price)

    response.headers["X-Total-Count"] = str(query.count())
    ordering = [rank] if rank is not None else []
    ordering += [models.Listing.created_at.desc(), models.Listing.id]  # stable, so pages never overlap
    page = with_relations(query).order_by(*ordering).limit(limit).offset(offset).all()
    return [_to_out(l) for l in page]


@router.get("/categories")
def list_categories():
    return models.CATEGORIES


@router.get("/{listing_id}", response_model=schemas.ListingOut)
def get_listing(listing_id: str, db: Session = Depends(get_db)):
    listing = with_relations(db.query(models.Listing)).filter(models.Listing.id == listing_id).first()
    # Listings awaiting admin review (restricted categories) or deactivated are not public.
    if not listing or listing.status != "live":
        raise HTTPException(status_code=404, detail="Listing not found")
    return _to_out(listing)


@router.patch("/{listing_id}/deactivate", response_model=schemas.ListingOut)
def deactivate_listing(
    listing_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role("vendor")),
):
    """FR-2.2 -- vendors can only edit/deactivate their own listings."""
    listing = db.query(models.Listing).filter(models.Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.vendor.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your listing")
    listing.status = "deactivated"
    db.commit()
    db.refresh(listing)
    return _to_out(listing)


@router.get("/vendor/mine", response_model=list[schemas.ListingOut])
def my_listings(db: Session = Depends(get_db), user: models.User = Depends(require_role("vendor"))):
    vendor = db.query(models.Vendor).filter(models.Vendor.user_id == user.id).first()
    listings = with_relations(db.query(models.Listing)).filter(
        models.Listing.vendor_id == vendor.id).order_by(models.Listing.created_at.desc()).all()
    return [_to_out(l) for l in listings]
