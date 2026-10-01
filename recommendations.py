from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import and_, func
from sqlalchemy.orm import Session, aliased

import models
import schemas
from database import get_db
from auth_utils import get_current_user
from routers.listings import _to_out, with_relations

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

COLD_START_INTERACTION_THRESHOLD = 3
CF_MIN_PLATFORM_INTERACTIONS = 20  # below this, prefer content-based over item-item CF
TOP_N = 8
CF_HISTORY_WINDOW = 20      # the user's most recent interactions that seed the CF lookup
CONTENT_CANDIDATE_LIMIT = 200  # content-based scoring looks at the best sellers, not the whole catalogue


def _available(query):
    return query.filter(models.Listing.status == "live", models.Listing.quantity > 0)


def _trending(db: Session, category: str = None) -> list[models.Listing]:
    """Cold-start path (FR-7.1): best-selling in-stock listings, optionally scoped to a category."""
    query = _available(with_relations(db.query(models.Listing)))
    if category:
        query = query.filter(models.Listing.category == category)
    return query.order_by(models.Listing.sales_count.desc(), models.Listing.created_at.desc()).limit(TOP_N).all()


def _content_based(db: Session, user_id: str) -> list[models.Listing]:
    """FR-7.2: score listings by category/price-band closeness to the user's history."""
    history_ids = [r[0] for r in db.query(models.Interaction.listing_id).filter(
        models.Interaction.user_id == user_id).distinct().limit(200).all()]
    history_listings = db.query(models.Listing).filter(models.Listing.id.in_(history_ids)).all() if history_ids else []
    if not history_listings:
        return _trending(db)

    categories = {l.category for l in history_listings}
    avg_price = sum(l.price for l in history_listings) / len(history_listings)

    base = _available(with_relations(db.query(models.Listing))).filter(~models.Listing.id.in_(history_ids))
    candidates = base.filter(models.Listing.category.in_(categories)) \
        .order_by(models.Listing.sales_count.desc()).limit(CONTENT_CANDIDATE_LIMIT).all()
    if len(candidates) < TOP_N:  # not enough in the user's categories: top up with best sellers elsewhere
        seen = {c.id for c in candidates}
        extra = base.order_by(models.Listing.sales_count.desc()).limit(TOP_N * 3).all()
        candidates += [l for l in extra if l.id not in seen]

    def score(listing):
        s = 0.0
        if listing.category in categories:
            s += 2.0
        price_diff = abs(listing.price - avg_price) / max(avg_price, 1)
        s += max(0, 1 - price_diff)  # closer price -> higher score
        return s

    return sorted(candidates, key=score, reverse=True)[:TOP_N]


def _co_purchase_counts(db: Session, seed_listing_ids: set[str]) -> dict[str, dict[str, int]]:
    """
    For each seed listing: {other_listing: number of paid orders containing both}.

    This is ONE aggregate query bounded by the orders that contain the user's few recent
    listings. The previous version loaded every confirmed order and walked each order's items
    in Python (one SQL query per order: 5,019 queries and ~7 s at 5,000 orders), and only counted
    orders still in the transient "confirmed_paid" state, so its data dried up as orders progressed.
    """
    if not seed_listing_ids:
        return {}
    a, b = aliased(models.OrderItem), aliased(models.OrderItem)
    rows = (
        db.query(a.listing_id, b.listing_id, func.count(func.distinct(a.order_id)))
        .join(b, and_(b.order_id == a.order_id, b.listing_id != a.listing_id))
        .join(models.Order, models.Order.id == a.order_id)
        .filter(models.Order.status.in_(models.PAID_STATUSES), a.listing_id.in_(list(seed_listing_ids)))
        .group_by(a.listing_id, b.listing_id)
        .all()
    )
    co: dict[str, dict[str, int]] = defaultdict(dict)
    for seed, other, n in rows:
        co[seed][other] = n
    return co


def _item_based_cf(db: Session, user_id: str) -> list[models.Listing]:
    """FR-7.3: item-item collaborative filtering from co-purchase history (Amazon-style)."""
    history = db.query(models.Interaction).filter(
        models.Interaction.user_id == user_id
    ).order_by(models.Interaction.created_at.desc()).limit(CF_HISTORY_WINDOW).all()

    if not history:
        return _trending(db)

    already_seen = {h.listing_id for h in history}
    co_occurrence = _co_purchase_counts(db, already_seen)

    scores = defaultdict(float)
    now = datetime.utcnow()
    for h in history:
        # more recent interactions weight more heavily, per Section 7.5 step 3c
        age_days = max((now - h.created_at).days, 0)
        recency_weight = 1.0 / (1 + age_days)
        for candidate, co_score in co_occurrence.get(h.listing_id, {}).items():
            if candidate not in already_seen:
                scores[candidate] += co_score * recency_weight

    if not scores:
        return _content_based(db, user_id)

    ranked_ids = sorted(scores, key=scores.get, reverse=True)[:TOP_N * 3]  # headroom for sold-out/removed items
    listings = _available(with_relations(db.query(models.Listing))).filter(models.Listing.id.in_(ranked_ids)).all()
    order_lookup = {lid: i for i, lid in enumerate(ranked_ids)}
    listings.sort(key=lambda l: order_lookup.get(l.id, 999))
    return listings[:TOP_N] or _content_based(db, user_id)


@router.get("", response_model=list[schemas.ListingOut])
def get_recommendations(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """Implements the tiered ranking algorithm, Section 7.5 / FR-7.1-7.4."""
    # Counts are capped at the threshold they are compared with: no need to scan a large table to learn "enough".
    interaction_count = db.query(models.Interaction.id).filter(
        models.Interaction.user_id == user.id).limit(COLD_START_INTERACTION_THRESHOLD).count()

    if interaction_count < COLD_START_INTERACTION_THRESHOLD:
        return [_to_out(l, reason="Trending") for l in _trending(db)]

    platform_volume = db.query(models.Interaction.id).limit(CF_MIN_PLATFORM_INTERACTIONS).count()
    if platform_volume < CF_MIN_PLATFORM_INTERACTIONS:
        return [_to_out(l, reason="Because you viewed similar items") for l in _content_based(db, user.id)]

    return [_to_out(l, reason="Customers who bought this also bought") for l in _item_based_cf(db, user.id)]


@router.get("/trending", response_model=list[schemas.ListingOut])
def trending_public(category: str = None, db: Session = Depends(get_db)):
    """Public, unauthenticated trending feed — what a brand-new visitor sees (FR-7.1)."""
    return [_to_out(l, reason="Trending") for l in _trending(db, category)]
