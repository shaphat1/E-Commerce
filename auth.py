import hashlib
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

import models
import schemas
import notifications
from database import get_db
from auth_utils import (
    hash_password, verify_password, burn_password_check, create_session, invalidate_session,
    invalidate_all_sessions_for_user, get_current_user,
)
from rate_limit import rate_limit, count_hits, record_hit, clear_hits

router = APIRouter(prefix="/auth", tags=["auth"])

RESET_OTP_TTL_MINUTES = 15
VERIFY_TOKEN_TTL_HOURS = 24

# Per-ACCOUNT throttles on top of the per-IP ones, so rotating IPs does not help an attacker.
LOGIN_FAIL_LIMIT, LOGIN_FAIL_WINDOW = 10, 900   # 10 failed logins / 15 min / account
OTP_FAIL_LIMIT, OTP_FAIL_WINDOW = 5, 900        # 5 wrong reset codes / 15 min / account


def _token_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


@router.post("/register", response_model=schemas.AuthResponse, dependencies=[Depends(rate_limit(20, 300))])
def register(payload: schemas.RegisterRequest, db: Session = Depends(get_db)):
    # FR-1.1/1.2 -- uniqueness check
    existing = db.query(models.User).filter(
        (models.User.email == payload.email) | (models.User.phone == payload.phone)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Account already exists")

    if payload.role == "vendor" and not (payload.business_name and payload.vendor_category):
        raise HTTPException(status_code=400, detail="Vendors must supply a business name and category")

    # payload.agreed_to_terms is already enforced True by the schema validator --
    # a request without it is rejected with 422 before this handler even runs.

    status_value = "pending_verification" if payload.role == "vendor" else "active"
    user = models.User(
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        role=payload.role,
        status=status_value,
        email_verified=False,
        agreed_to_terms=payload.agreed_to_terms,
    )
    db.add(user)
    db.flush()  # assign user.id before creating the vendor row

    if payload.role == "vendor":
        vendor = models.Vendor(
            user_id=user.id,
            business_name=payload.business_name,
            category=payload.vendor_category,
            verification_status="pending",
        )
        db.add(vendor)

    # Issue an email verification token (store only its hash) and "send" it.
    raw_token = secrets.token_urlsafe(24)
    db.add(models.EmailVerificationToken(
        user_id=user.id, token_hash=_token_hash(raw_token),
        expires_at=datetime.utcnow() + timedelta(hours=VERIFY_TOKEN_TTL_HOURS),
    ))

    db.commit()
    db.refresh(user)

    notifications.notify_verify_email(user.email, raw_token)

    token = create_session(db, user.id)
    return schemas.AuthResponse(
        token=token, user_id=user.id, name=user.name, role=user.role, status=user.status
    )


@router.post("/login", response_model=schemas.AuthResponse, dependencies=[Depends(rate_limit(20, 300))])
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    fail_key = f"login-fail:{payload.email.lower()}"
    if count_hits(db, fail_key, LOGIN_FAIL_WINDOW) >= LOGIN_FAIL_LIMIT:
        raise HTTPException(status_code=429, detail="Too many failed attempts for this account. Try again later.",
                            headers={"Retry-After": str(LOGIN_FAIL_WINDOW)})

    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user:
        burn_password_check(payload.password)  # same timing whether or not the email exists
    if not user or user.status == "deleted" or not verify_password(payload.password, user.password_hash):
        record_hit(db, fail_key)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    clear_hits(db, fail_key)
    token = create_session(db, user.id)
    return schemas.AuthResponse(
        token=token, user_id=user.id, name=user.name, role=user.role, status=user.status
    )


@router.post("/logout")
def logout(authorization: str = Header(default=""), db: Session = Depends(get_db)):
    invalidate_session(db, authorization)
    return {"logged_out": True}


@router.get("/me")
def me(user: models.User = Depends(get_current_user)):
    return {
        "id": user.id, "name": user.name, "email": user.email,
        "role": user.role, "status": user.status, "email_verified": user.email_verified,
    }


# ---------- Email verification ----------

@router.post("/verify-email")
def verify_email(payload: schemas.EmailVerificationConfirm, db: Session = Depends(get_db)):
    token_hash = _token_hash(payload.token)
    record = db.query(models.EmailVerificationToken).filter(
        models.EmailVerificationToken.token_hash == token_hash,
        models.EmailVerificationToken.used == False,  # noqa: E712
    ).first()
    if not record or record.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    user = db.query(models.User).filter(models.User.id == record.user_id).first()
    user.email_verified = True
    record.used = True
    db.commit()
    return {"verified": True}


# ---------- Password reset (forgot password), FR-1.3 ----------

@router.post("/password-reset/request", dependencies=[Depends(rate_limit(10, 900))])
def request_password_reset(payload: schemas.PasswordResetRequest, db: Session = Depends(get_db)):
    """
    Always returns the same generic response whether or not the email
    exists -- this deliberately avoids leaking which emails are registered
    (a common account-enumeration vector).
    """
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if user:
        otp = f"{secrets.randbelow(1_000_000):06d}"
        db.add(models.PasswordResetToken(
            user_id=user.id, token_hash=_token_hash(otp),
            expires_at=datetime.utcnow() + timedelta(minutes=RESET_OTP_TTL_MINUTES),
        ))
        db.commit()
        notifications.notify_password_reset(user.email, otp)

    return {"message": "If that email is registered, a reset code has been sent."}


@router.post("/password-reset/confirm", dependencies=[Depends(rate_limit(10, 900))])
def confirm_password_reset(payload: schemas.PasswordResetConfirm, db: Session = Depends(get_db)):
    # A 6-digit code has only 1,000,000 values: without these throttles it can be brute-forced
    # inside its 15-minute lifetime and the account taken over.
    otp_key = f"otp-fail:{payload.email.lower()}"
    if count_hits(db, otp_key, OTP_FAIL_WINDOW) >= OTP_FAIL_LIMIT:
        raise HTTPException(status_code=429, detail="Too many incorrect codes. Request a new code later.",
                            headers={"Retry-After": str(OTP_FAIL_WINDOW)})

    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user:
        record_hit(db, otp_key)
        raise HTTPException(status_code=400, detail="Invalid code")

    token_hash = _token_hash(payload.otp)
    record = db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.user_id == user.id,
        models.PasswordResetToken.token_hash == token_hash,
        models.PasswordResetToken.used == False,  # noqa: E712
    ).first()
    if not record or record.expires_at < datetime.utcnow():
        record_hit(db, otp_key)
        raise HTTPException(status_code=400, detail="Invalid or expired code")

    user.password_hash = hash_password(payload.new_password)
    record.used = True
    db.commit()

    # Force re-login everywhere -- a password reset should invalidate old sessions,
    # same principle as account deletion (routers/users.py).
    invalidate_all_sessions_for_user(db, user.id)
    clear_hits(db, otp_key)

    return {"reset": True}
