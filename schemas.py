from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

import models

BCRYPT_MAX_BYTES = 72  # bcrypt cannot hash more than this; longer passwords used to cause HTTP 500


def _check_password(v: str) -> str:
    if len(v) < 8 or not any(c.isdigit() for c in v):
        raise ValueError("Password must be at least 8 characters and include a number")
    if len(v.encode()) > BCRYPT_MAX_BYTES:
        raise ValueError("Password must be at most 72 bytes long")
    return v


# ---------- Auth ----------

class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=20)
    password: str
    role: str = "buyer"  # buyer | vendor
    business_name: Optional[str] = Field(default=None, max_length=150)
    vendor_category: Optional[str] = None
    agreed_to_terms: bool = False

    @field_validator("password")
    @classmethod
    def strong_password(cls, v):
        return _check_password(v)

    @field_validator("role")
    @classmethod
    def valid_role(cls, v):
        if v not in ("buyer", "vendor"):
            raise ValueError("role must be 'buyer' or 'vendor'")
        return v

    @field_validator("vendor_category")
    @classmethod
    def valid_vendor_category(cls, v):
        if v is not None and v not in models.CATEGORIES:
            raise ValueError("Unknown vendor category")
        return v

    @field_validator("agreed_to_terms")
    @classmethod
    def must_agree(cls, v):
        if not v:
            raise ValueError("You must agree to the Terms of Service and Privacy Policy to register")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(max_length=256)


class AuthResponse(BaseModel):
    token: str
    user_id: str
    name: str
    role: str
    status: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, v):
        return _check_password(v)


class EmailVerificationConfirm(BaseModel):
    token: str = Field(max_length=200)


# ---------- Listings ----------

class ListingCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    category: str
    description: str = Field(default="", max_length=5000)
    price: float = Field(gt=0, le=100_000_000)
    quantity: int = Field(ge=0, le=100_000)
    delivery_options: str = Field(default="pickup", max_length=100)
    photo_urls: List[str] = []

    @field_validator("category")
    @classmethod
    def valid_category(cls, v):
        if v not in models.CATEGORIES:
            raise ValueError("Unknown category")
        return v

    @field_validator("photo_urls")
    @classmethod
    def photo_rules(cls, v):
        if len(v) < 1 or len(v) > 5:
            raise ValueError("Attach between 1 and 5 photos")
        for url in v:
            if len(url) > 2048 or not url.lower().startswith(("http://", "https://")):
                raise ValueError("Photo URLs must be http(s) links under 2048 characters")
        return v


class ListingOut(BaseModel):
    id: str
    vendor_id: str
    vendor_name: str
    title: str
    category: str
    description: str
    price: float
    quantity: int
    status: str
    photo_urls: List[str] = []
    vendor_rating: Optional[float] = None
    reason: Optional[str] = None  # recommendation explanation tag, FR-7.4 / FR-3.4

    class Config:
        from_attributes = True


# ---------- Cart / Checkout ----------

class CartItem(BaseModel):
    listing_id: str = Field(max_length=36)
    quantity: int = Field(gt=0, le=100_000)  # same ceiling as a listing's stock, so over-asking gets a clear 400 "not enough stock"


class CheckoutRequest(BaseModel):
    items: List[CartItem] = Field(max_length=50)
    delivery_address: str = Field(max_length=500)
    payment_method: Literal["card", "bank_transfer", "ussd", "pay_on_delivery"] = "card"


class OrderOut(BaseModel):
    id: str
    vendor_id: str
    vendor_name: Optional[str] = None
    buyer_id: str
    session_id: str
    subtotal: Optional[float] = None
    vat_amount: Optional[float] = None
    delivery_fee: Optional[float] = None
    total: float
    status: str
    delivery_address: str
    created_at: datetime
    # Set only while status == "pending_payment" on a live gateway: where the buyer pays.
    payment_url: Optional[str] = None
    payment_reference: Optional[str] = None

    class Config:
        from_attributes = True


class OrderStatusUpdate(BaseModel):
    new_status: str = Field(max_length=40)


# ---------- Reviews ----------

class ReviewCreate(BaseModel):
    order_id: str = Field(max_length=36)
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=2000)


# ---------- Disputes ----------

class DisputeCreate(BaseModel):
    order_id: str = Field(max_length=36)
    reason: str = Field(max_length=2000)


class DisputeResolution(BaseModel):
    refund: bool
