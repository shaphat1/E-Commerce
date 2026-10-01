"""
ORM models -- one class per entity in the report's Section 8.1 ERD.
IDs are UUID strings (stored as CHAR(36)) to match the ERD's `uuid` typing
without depending on a database-specific UUID column type, so this same
model file works unchanged against SQLite (dev) or Postgres (production).

Foreign-key columns are indexed explicitly: PostgreSQL does not index them
automatically, and every list/join in the API filters on one.
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Float, Integer, DateTime, ForeignKey, Text, Boolean,
    CheckConstraint, Index, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from database import Base


def new_id():
    return str(uuid.uuid4())


# Restricted categories require vendor pre-approval + a whitelist,
# per Section 2.4 (Legal Feasibility) and FR-2.4.
RESTRICTED_CATEGORIES = {"Pharmacy & Health"}

VAT_RATE = 0.075  # Nigeria standard VAT rate, applied to items subtotal at checkout (Section 5.3/7.3)

CATEGORIES = [
    "Books & Study Materials",
    "Electronics & Gadgets",
    "Fashion & Accessories",
    "Groceries & Provisions",
    "Pharmacy & Health",
    "Food & Snacks",
    "Services",
    "Hostel & Room Essentials",
]

ORDER_STATUS_FLOW = {
    "pending_payment": ["confirmed_paid", "payment_failed"],
    "confirmed_paid": ["confirmed", "payment_failed"],
    "confirmed": ["ready_for_delivery"],
    "ready_for_delivery": ["completed"],
    "completed": [],
    "payment_failed": [],
    "refunded": [],
}

# Every status in which the buyer's payment has been accepted. Revenue (GMV),
# the recommender's co-purchase data and dispute eligibility must count ALL of
# these -- counting only "confirmed_paid" made them shrink as orders progressed.
PAID_STATUSES = ("confirmed_paid", "confirmed", "ready_for_delivery", "completed")


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=new_id)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    phone = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="buyer")  # buyer | vendor | admin
    status = Column(String, nullable=False, default="active")
    email_verified = Column(Boolean, nullable=False, default=False)
    agreed_to_terms = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    vendor_profile = relationship("Vendor", back_populates="user", uselist=False)


class UserSession(Base):
    """
    Server-side login session. Only the SHA-256 of the bearer token is stored,
    so a database leak does not leak usable tokens. Living in the database
    (not process memory) is what lets the API run as several instances.
    """
    __tablename__ = "user_sessions"

    token_hash = Column(String(64), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class RateLimitHit(Base):
    """One row per rate-limited attempt; counted over a sliding window. Shared across instances."""
    __tablename__ = "rate_limit_hits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (Index("ix_rate_hits_key_created", "key", "created_at"),)


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(String(36), primary_key=True, default=new_id)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True)
    business_name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    verification_status = Column(String, nullable=False, default="pending")  # pending | approved | rejected

    user = relationship("User", back_populates="vendor_profile")
    listings = relationship("Listing", back_populates="vendor")


class Listing(Base):
    __tablename__ = "listings"

    id = Column(String(36), primary_key=True, default=new_id)
    vendor_id = Column(String(36), ForeignKey("vendors.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    category = Column(String, nullable=False)
    description = Column(Text, default="")
    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    status = Column(String, nullable=False, default="live")  # live | pending_admin_review | deactivated
    delivery_options = Column(String, default="pickup")
    created_at = Column(DateTime, default=datetime.utcnow)
    sales_count = Column(Integer, default=0)  # used by the trending/cold-start recommender

    vendor = relationship("Vendor", back_populates="listings")
    photos = relationship("ListingPhoto", back_populates="listing")

    __table_args__ = (
        # Last line of defence against overselling: even if application code regressed,
        # the database refuses to let stock go negative.
        CheckConstraint("quantity >= 0", name="ck_listing_quantity_nonneg"),
        Index("ix_listings_status_category", "status", "category"),
        Index("ix_listings_status_sales", "status", "sales_count"),
    )


class ListingPhoto(Base):
    __tablename__ = "listing_photos"

    id = Column(String(36), primary_key=True, default=new_id)
    listing_id = Column(String(36), ForeignKey("listings.id"), nullable=False, index=True)
    url = Column(String, nullable=False)

    listing = relationship("Listing", back_populates="photos")


class Order(Base):
    __tablename__ = "orders"

    id = Column(String(36), primary_key=True, default=new_id)
    buyer_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    vendor_id = Column(String(36), ForeignKey("vendors.id"), nullable=False, index=True)
    session_id = Column(String(36), nullable=False, index=True)  # groups a multi-vendor checkout
    subtotal = Column(Float, nullable=False, default=0.0)
    vat_amount = Column(Float, nullable=False, default=0.0)
    delivery_fee = Column(Float, nullable=False, default=0.0)
    total = Column(Float, nullable=False)
    status = Column(String, nullable=False, default="pending_payment", index=True)
    payment_reference = Column(String, nullable=True, index=True)  # gateway reference; needed to verify and refund
    payment_url = Column(String, nullable=True)  # hosted-checkout URL while status is pending_payment
    expires_at = Column(DateTime, nullable=True)  # a pending order's stock reservation lapses at this time
    delivery_address = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = relationship("OrderItem", back_populates="order")
    vendor = relationship("Vendor")
    buyer = relationship("User")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(String(36), primary_key=True, default=new_id)
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False, index=True)
    listing_id = Column(String(36), ForeignKey("listings.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    price_at_purchase = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    listing = relationship("Listing")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(String(36), primary_key=True, default=new_id)
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False)
    buyer_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    vendor_id = Column(String(36), ForeignKey("vendors.id"), nullable=False, index=True)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    # One review per order, enforced by the database (the router's pre-check alone is racy).
    __table_args__ = (UniqueConstraint("order_id", name="uq_review_order"),)


class Interaction(Base):
    """Append-only behaviour log powering the recommendation engine (FR-7.1-7.3)."""
    __tablename__ = "interactions"

    id = Column(String(36), primary_key=True, default=new_id)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    listing_id = Column(String(36), ForeignKey("listings.id"), nullable=False, index=True)
    type = Column(String, nullable=False)  # view | purchase
    created_at = Column(DateTime, default=datetime.utcnow)

    listing = relationship("Listing")


class Dispute(Base):
    __tablename__ = "disputes"

    id = Column(String(36), primary_key=True, default=new_id)
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False, index=True)
    buyer_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    status = Column(String, nullable=False, default="open", index=True)  # open | resolved_no_refund | refunded
    reason = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(String(36), primary_key=True, default=new_id)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String, nullable=False, index=True)  # never store the raw token
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"

    id = Column(String(36), primary_key=True, default=new_id)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
