"""
Password hashing (bcrypt, FR-1.3 / NFR-Security) and database-backed bearer sessions.

Sessions live in the `user_sessions` table (only a SHA-256 of the token is stored),
so any number of API instances behind a load balancer agree on who is logged in.
"""
import hashlib
import secrets
from datetime import datetime, timedelta

import bcrypt
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session

from database import get_db
import models

SESSION_TTL_SECONDS = 24 * 60 * 60  # 24 hours
BCRYPT_MAX_BYTES = 72  # bcrypt rejects/ignores anything longer; we reject it up front

# Compared against when the email is unknown, so "no such user" and "wrong password"
# take the same time and can't be told apart by timing.
_DUMMY_HASH = bcrypt.hashpw(b"maumart-dummy-password", bcrypt.gensalt()).decode()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:  # e.g. password longer than bcrypt's 72-byte limit
        return False


def burn_password_check(password: str) -> None:
    """Equalise login timing for unknown emails."""
    verify_password(password, _DUMMY_HASH)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(db: Session, user_id: str) -> str:
    now = datetime.utcnow()
    db.query(models.UserSession).filter(models.UserSession.expires_at < now).delete(synchronize_session=False)
    token = secrets.token_urlsafe(32)
    db.add(models.UserSession(
        token_hash=_hash_token(token), user_id=user_id,
        expires_at=now + timedelta(seconds=SESSION_TTL_SECONDS),
    ))
    db.commit()
    return token


def _bearer_token(authorization: str) -> str:
    scheme, _, token = (authorization or "").partition(" ")
    return token.strip() if scheme.lower() == "bearer" else ""


def invalidate_session(db: Session, authorization_header: str) -> None:
    token = _bearer_token(authorization_header)
    if token:
        db.query(models.UserSession).filter(
            models.UserSession.token_hash == _hash_token(token)
        ).delete(synchronize_session=False)
        db.commit()


def invalidate_all_sessions_for_user(db: Session, user_id: str) -> None:
    """Used on account deletion and password reset -- kills every active token for this user."""
    db.query(models.UserSession).filter(models.UserSession.user_id == user_id).delete(synchronize_session=False)
    db.commit()


def get_current_user(
    authorization: str = Header(default=""), db: Session = Depends(get_db)
) -> models.User:
    token = _bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    now = datetime.utcnow()
    row = (
        db.query(models.User, models.UserSession.expires_at)
        .join(models.UserSession, models.UserSession.user_id == models.User.id)
        .filter(models.UserSession.token_hash == _hash_token(token))
        .first()
    )
    if not row:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user, expires_at = row
    if expires_at < now:
        db.query(models.UserSession).filter(
            models.UserSession.token_hash == _hash_token(token)
        ).delete(synchronize_session=False)
        db.commit()
        raise HTTPException(status_code=401, detail="Session expired, please log in again")
    if user.status == "deleted":
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def require_role(*roles):
    def checker(user: models.User = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Not authorized for this action")
        return user
    return checker
