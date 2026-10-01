"""
Environment-driven configuration and production safety checks.

MAUMART_ENV=production turns on fail-closed startup validation: the app
refuses to boot with settings that are fine for a laptop but unsafe on the
internet (mock payments, console email that logs reset codes, SQLite,
wildcard CORS, ...). In development nothing here blocks startup.
"""
import os
import logging

logger = logging.getLogger("maumart.config")

DEFAULT_DEV_ORIGINS = (
    "http://127.0.0.1:8550,http://localhost:8550,http://127.0.0.1:8551,http://localhost:8551"
)


def env() -> str:
    return os.environ.get("MAUMART_ENV", "development").strip().lower()


def is_production() -> bool:
    return env() in ("production", "prod")


def pilot_cod_only() -> bool:
    """
    Pilot switch: with the mock gateway, production may run ONLY if every order is pay-on-delivery.
    Checkout rejects all other payment methods in that mode (see routers/cart.py), so the mock
    can never mark a card/transfer order "paid" without money moving.
    """
    return os.environ.get("MAUMART_PILOT_COD_ONLY", "").strip() == "1"


def allowed_origins() -> list[str]:
    raw = os.environ.get("MAUMART_ALLOWED_ORIGINS", DEFAULT_DEV_ORIGINS)
    return [o.strip() for o in raw.split(",") if o.strip()]


def validate_production_config() -> list[str]:
    """
    Raises RuntimeError listing every fatal misconfiguration when running in
    production; returns a list of non-fatal warnings (also logged).
    Does nothing outside production.
    """
    if not is_production():
        return []

    errors: list[str] = []
    warnings: list[str] = []

    db_url = os.environ.get("DATABASE_URL", "sqlite:///./maumart.db")
    if db_url.startswith("sqlite"):
        errors.append("DATABASE_URL must point at PostgreSQL in production (SQLite is dev-only).")

    if "MAUMART_ALLOWED_ORIGINS" not in os.environ:
        errors.append("MAUMART_ALLOWED_ORIGINS must be set to the real frontend origin(s).")
    elif "*" in allowed_origins():
        errors.append("MAUMART_ALLOWED_ORIGINS must not contain '*'.")

    if os.environ.get("MAUMART_PAYMENT_MOCK", "true").strip().lower() != "false":
        if not pilot_cod_only():
            errors.append(
                "MAUMART_PAYMENT_MOCK must be 'false' in production: the mock gateway marks every "
                "payment successful without moving money. For a cash-on-delivery-only pilot, "
                "set MAUMART_PILOT_COD_ONLY=1 instead."
            )
        else:
            warnings.append("PILOT MODE: only pay_on_delivery is accepted; card/transfer/USSD are refused.")
    elif not os.environ.get("MAUMART_PAYSTACK_SECRET_KEY"):
        errors.append("MAUMART_PAYSTACK_SECRET_KEY is required when the mock gateway is off.")

    if os.environ.get("MAUMART_NOTIFY_BACKEND", "console").strip().lower() != "smtp":
        errors.append(
            "MAUMART_NOTIFY_BACKEND must be 'smtp' in production: the console backend writes "
            "password-reset codes and verification tokens into the server log."
        )
    elif not os.environ.get("MAUMART_SMTP_HOST"):
        errors.append("MAUMART_SMTP_HOST is required when MAUMART_NOTIFY_BACKEND=smtp.")

    app_url = os.environ.get("MAUMART_APP_URL", "")
    if not app_url.startswith("https://"):
        warnings.append("MAUMART_APP_URL should be an https:// URL in production.")

    if os.environ.get("MAUMART_ENABLE_HSTS", "").strip() != "1":
        warnings.append("HSTS is off. Set MAUMART_ENABLE_HSTS=1 once HTTPS is confirmed working.")

    if errors:
        raise RuntimeError(
            "Refusing to start in production with unsafe configuration:\n  - " + "\n  - ".join(errors)
        )
    for w in warnings:
        logger.warning(w)
    return warnings
