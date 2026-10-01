"""
Database-backed sliding-window rate limiting.

Counters live in the `rate_limit_hits` table rather than process memory, so
limits hold across multiple API instances and survive restarts. Two uses:

  * rate_limit(n, window)  -- FastAPI dependency, per client IP + path.
  * count_hits / record_hit -- building blocks for per-ACCOUNT limits
    (failed logins, failed reset-code guesses), which an attacker rotating
    IPs cannot sidestep.

Behind a reverse proxy, request.client.host is the proxy's address unless
uvicorn is told to trust X-Forwarded-For (--proxy-headers together with
FORWARDED_ALLOW_IPS=<proxy address>); otherwise every user shares one bucket.
See DEPLOYMENT.md.
"""
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

import models
from database import get_db


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def count_hits(db: Session, key: str, window_seconds: int) -> int:
    cutoff = datetime.utcnow() - timedelta(seconds=window_seconds)
    return db.query(func.count(models.RateLimitHit.id)).filter(
        models.RateLimitHit.key == key, models.RateLimitHit.created_at > cutoff
    ).scalar() or 0


def record_hit(db: Session, key: str) -> None:
    db.add(models.RateLimitHit(key=key))
    db.commit()


def clear_hits(db: Session, key: str) -> None:
    db.query(models.RateLimitHit).filter(models.RateLimitHit.key == key).delete(synchronize_session=False)
    db.commit()


def rate_limit(max_attempts: int, window_seconds: int):
    """FastAPI dependency factory: `Depends(rate_limit(5, 60))` = 5 attempts per 60s per IP."""

    def checker(request: Request, db: Session = Depends(get_db)):
        key = f"{request.url.path}:{_client_key(request)}"
        if count_hits(db, key, window_seconds) >= max_attempts:
            raise HTTPException(
                status_code=429,
                detail="Too many attempts. Try again in a moment.",
                headers={"Retry-After": str(window_seconds)},
            )
        record_hit(db, key)

    return checker


def purge_old_hits(db: Session, older_than_seconds: int = 86400) -> int:
    cutoff = datetime.utcnow() - timedelta(seconds=older_than_seconds)
    n = db.query(models.RateLimitHit).filter(models.RateLimitHit.created_at < cutoff).delete(synchronize_session=False)
    db.commit()
    return n
