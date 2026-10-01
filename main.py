import os
import time
import logging
import threading
import json as jsonlib
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import PlainTextResponse

import config
from database import init_db, SessionLocal, engine
from sqlalchemy import text
from routers import (
    auth, listings, cart, orders, reviews, recommendations, admin,
    interactions, users, storefront, payments,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------- Structured logging ----------
# JSON lines to stdout -- the format any real log aggregator (CloudWatch, Loki,
# a plain `docker logs | jq`) expects, rather than plain unstructured text.
logging.basicConfig(level=logging.INFO, format="%(message)s")
access_logger = logging.getLogger("maumart.access")
error_logger = logging.getLogger("maumart.errors")

SWEEP_INTERVAL_SECONDS = int(os.environ.get("MAUMART_SWEEP_INTERVAL", "60"))
ENABLE_HSTS = os.environ.get("MAUMART_ENABLE_HSTS", "").strip() == "1"


def _sweeper(stop: threading.Event):
    """Background housekeeping: release lapsed stock reservations, trim old rate-limit rows."""
    import order_service
    from rate_limit import purge_old_hits
    ticks = 0
    while not stop.wait(SWEEP_INTERVAL_SECONDS):
        db = SessionLocal()
        try:
            n = order_service.expire_stale_reservations(db)
            if n:
                access_logger.info(jsonlib.dumps({"event": "reservations_released", "count": n}))
            ticks += 1
            if ticks % 60 == 0:
                purge_old_hits(db)
        except Exception:
            error_logger.exception(jsonlib.dumps({"event": "sweeper_error"}))
            db.rollback()
        finally:
            db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    config.validate_production_config()   # fail closed on unsafe production settings
    init_db()
    stop = threading.Event()
    thread = threading.Thread(target=_sweeper, args=(stop,), daemon=True, name="sweeper")
    thread.start()
    yield
    stop.set()


app = FastAPI(
    title="MAUMart API", version="1.0.0", lifespan=lifespan,
    # Interactive docs are handy in development but advertise the whole API surface in production.
    docs_url=None if config.is_production() else "/docs",
    redoc_url=None if config.is_production() else "/redoc",
    openapi_url=None if config.is_production() else "/openapi.json",
)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    start = time.time()
    try:
        response = await call_next(request)
    except Exception:
        error_logger.exception(jsonlib.dumps({
            "event": "unhandled_exception", "path": request.url.path, "method": request.method,
        }))
        raise
    duration_ms = round((time.time() - start) * 1000, 1)
    log_fn = access_logger.warning if response.status_code >= 500 else access_logger.info
    log_fn(jsonlib.dumps({
        "event": "request", "method": request.method, "path": request.url.path,
        "status": response.status_code, "duration_ms": duration_ms,
        "client": request.client.host if request.client else None,
    }))
    return response


# In production, MAUMART_ALLOWED_ORIGINS must list the real frontend origin(s)
# (startup refuses "*" or an unset value there).
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.allowed_origins(),
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """
    Baseline security headers. HSTS is opt-in (MAUMART_ENABLE_HSTS=1): sending it before TLS
    actually works would lock browsers out. Turn it on once HTTPS is confirmed.
    """
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if request.url.path.startswith("/store"):
        # Storefront pages are server-rendered with no inline scripts apart from the JSON-LD data block.
        response.headers.setdefault("Content-Security-Policy",
                                    "default-src 'self'; img-src 'self' https: data:; style-src 'self'; "
                                    "frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
    if ENABLE_HSTS:
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
    return response


app.include_router(auth.router)
app.include_router(listings.router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(payments.router)
app.include_router(reviews.router)
app.include_router(recommendations.router)
app.include_router(admin.router)
app.include_router(interactions.router)
app.include_router(users.router)
app.include_router(storefront.router)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

LEGAL_DOCS = {"TERMS_OF_SERVICE", "PRIVACY_POLICY", "REFUND_POLICY", "VENDOR_AGREEMENT"}


@app.get("/{doc_name}.md", response_class=PlainTextResponse)
def serve_legal_doc(doc_name: str):
    """Serves the legal documents linked from the storefront footer (Terms, Privacy, etc.)."""
    if doc_name not in LEGAL_DOCS:
        return PlainTextResponse("Not found", status_code=404)
    # In the Docker image the docs are copied next to the app (./legal); in the repo they sit one level up.
    for base in (os.path.join(BASE_DIR, "legal"), os.path.join(BASE_DIR, "..")):
        path = os.path.join(base, f"{doc_name}.md")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return PlainTextResponse(f.read())
    return PlainTextResponse("Not found", status_code=404)


@app.get("/")
def root():
    return {"service": "MAUMart API", "status": "ok"}


@app.get("/healthz")
def healthz():
    """Liveness + database reachability, for load balancers and the container healthcheck."""
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok"}
