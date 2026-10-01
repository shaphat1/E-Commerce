"""
Pluggable notification backend.

Honesty note for the coursework report: this sandbox has no network route
to a real SMTP relay or transactional-email API (no such domains are
network-allowed here), so `SMTPNotificationBackend` below is real,
correct smtplib code that has been verified end-to-end against a LOCAL
test SMTP server (see tests/test_notifications.py) -- not against a real
inbox. `ConsoleNotificationBackend` is what actually runs by default in
this environment, and is a completely normal pattern for dev/staging.

Switch backends via the MAUMART_NOTIFY_BACKEND env var: "console" (default)
or "smtp" (reads MAUMART_SMTP_HOST/PORT/USER/PASSWORD/FROM).
"""
import os
import smtplib
import logging
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from email.message import EmailMessage

logger = logging.getLogger("maumart.notifications")


class NotificationBackend(ABC):
    @abstractmethod
    def send(self, to_email: str, subject: str, body: str) -> bool:
        ...


class ConsoleNotificationBackend(NotificationBackend):
    """
    Logs the notification instead of delivering it. Default backend for development.
    NOT for production: the log line contains password-reset codes and verification
    tokens. config.validate_production_config() refuses to boot with it in production.
    """

    def send(self, to_email: str, subject: str, body: str) -> bool:
        logger.info("NOTIFY to=%s subject=%r body=%r", to_email, subject, body)
        return True


class SMTPNotificationBackend(NotificationBackend):
    """Real SMTP delivery. Verified locally against aiosmtpd -- see tests/test_notifications.py."""

    def __init__(self):
        self.host = os.environ["MAUMART_SMTP_HOST"]
        self.port = int(os.environ.get("MAUMART_SMTP_PORT", "587"))
        self.user = os.environ.get("MAUMART_SMTP_USER")
        self.password = os.environ.get("MAUMART_SMTP_PASSWORD")
        self.from_addr = os.environ.get("MAUMART_SMTP_FROM", "no-reply@maumart.ng")
        self.use_tls = os.environ.get("MAUMART_SMTP_TLS", "true").lower() == "true"

    def send(self, to_email: str, subject: str, body: str) -> bool:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.from_addr
        msg["To"] = to_email
        msg.set_content(body)

        try:
            with smtplib.SMTP(self.host, self.port, timeout=10) as smtp:
                if self.use_tls:
                    smtp.starttls()
                if self.user and self.password:
                    smtp.login(self.user, self.password)
                smtp.send_message(msg)
            return True
        except Exception:
            logger.exception("SMTP send failed to=%s subject=%r", to_email, subject)
            return False


_backend_cache: NotificationBackend | None = None


def get_backend() -> NotificationBackend:
    global _backend_cache
    if _backend_cache is not None:
        return _backend_cache
    kind = os.environ.get("MAUMART_NOTIFY_BACKEND", "console")
    _backend_cache = SMTPNotificationBackend() if kind == "smtp" else ConsoleNotificationBackend()
    return _backend_cache


def reset_backend_cache():
    """Test hook -- forces get_backend() to re-read env vars on next call."""
    global _backend_cache
    _backend_cache = None


# ---------- Delivery ----------
# SMTP can take up to its 10 s timeout. Sending inline would hold an API worker (and the user's
# request) for that long on every register / order / status change, so real delivery is handed
# to a small thread pool. send() already logs failures; a failed email must never fail the request.
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="notify")


def _dispatch(to_email: str, subject: str, body: str) -> None:
    backend = get_backend()
    if isinstance(backend, ConsoleNotificationBackend) or os.environ.get("MAUMART_NOTIFY_SYNC") == "1":
        backend.send(to_email, subject, body)  # cheap/log-only, or tests that need determinism
    else:
        _executor.submit(backend.send, to_email, subject, body)


# ---------- Templated sends used by the routers ----------

def notify_order_placed(to_email: str, order_id: str, total: float, vendor_name: str):
    _dispatch(
        to_email, "Your MAUMart order is confirmed",
        f"Order {order_id} with {vendor_name} for \u20a6{total:,.0f} has been placed and paid.",
    )


def notify_vendor_new_order(to_email: str, order_id: str, total: float):
    _dispatch(
        to_email, "New MAUMart order received",
        f"You have a new order ({order_id}) for \u20a6{total:,.0f}. Check your vendor dashboard.",
    )


def notify_order_status_changed(to_email: str, order_id: str, new_status: str):
    _dispatch(
        to_email, "Your MAUMart order status changed",
        f"Order {order_id} is now: {new_status.replace('_', ' ')}.",
    )


def notify_order_refunded(to_email: str, order_id: str, total: float):
    _dispatch(
        to_email, "Your MAUMart order was refunded",
        f"Order {order_id} for \u20a6{total:,.0f} has been refunded following a dispute review.",
    )


def notify_password_reset(to_email: str, otp: str):
    _dispatch(
        to_email, "Your MAUMart password reset code",
        f"Your one-time code is {otp}. It expires in 15 minutes. "
        f"If you didn't request this, you can ignore this email.",
    )


def notify_verify_email(to_email: str, token: str):
    _dispatch(
        to_email, "Verify your MAUMart email",
        f"Your verification code is {token}. It expires in 24 hours.",
    )
