"""
Payment gateway integration.

Two implementations behind one interface:

* MockGateway -- synchronous; charge() returns success immediately and moves
  no money. Development and tests only. The app REFUSES TO START with it when
  MAUMART_ENV=production (see config.validate_production_config).
* PaystackGateway -- the real asynchronous flow:
    1. charge() calls /transaction/initialize and returns status "pending"
       plus an authorization_url; the buyer pays on Paystack's hosted page.
    2. Paystack calls our webhook (routers/payments.py), whose HMAC-SHA512
       signature is verified by verify_webhook_signature(), and/or the buyer's
       app calls POST /payments/verify/{reference} which uses verify() below.
    3. Either path confirms the orders idempotently (order_service.py).

VERIFICATION STATUS -- read before going live:
  * The logic around this class (pending state, signature-checked webhook,
    idempotent confirmation, amount check, expiry, late-payment recovery) is
    covered by tests/test_payment_flow.py, which runs against a LOCAL STUB of
    Paystack's HTTP API (set MAUMART_PAYSTACK_BASE_URL to point at it).
  * The request/response shapes follow Paystack's documented API, but THIS CODE
    HAS NOT BEEN RUN AGAINST api.paystack.co. Before taking real money, run one
    full payment in Paystack TEST mode (test secret key, test card) from a
    network that can reach it and confirm the webhook arrives and is accepted.
"""
import os
import hmac
import hashlib
import logging
import uuid

import requests

logger = logging.getLogger("maumart.payments")

HTTP_TIMEOUT = 15


def paystack_base_url() -> str:
    # Overridable so the test suite can point the real client at a local stub.
    return os.environ.get("MAUMART_PAYSTACK_BASE_URL", "https://api.paystack.co").rstrip("/")


def to_kobo(amount_naira: float) -> int:
    """Naira -> kobo with rounding (int(x * 100) truncates: 19.99 * 100 == 1998.999...)."""
    return int(round(amount_naira * 100))


def verify_webhook_signature(raw_body: bytes, signature_header: str, secret_key: str) -> bool:
    """
    Paystack signs webhook payloads as HMAC-SHA512(secret_key, raw_body),
    sent in the `x-paystack-signature` header. Reject anything that doesn't
    match -- this is what stops an attacker from POSTing a fake
    "payment succeeded" webhook directly to your server.
    """
    if not signature_header:
        return False
    computed = hmac.new(secret_key.encode(), raw_body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(computed, signature_header)


class MockGateway:
    """Development/test gateway -- see module docstring. Moves no money."""

    _processed: dict[str, dict] = {}

    def charge(self, amount: float, method: str, idempotency_key: str, email: str = None, callback_url: str = None) -> dict:
        if idempotency_key in self._processed:
            return self._processed[idempotency_key]

        if amount <= 0:
            result = {"status": "failed", "reference": None}
        else:
            result = {"status": "success", "reference": f"MOCK-{uuid.uuid4().hex[:10]}"}

        self._processed[idempotency_key] = result
        return result

    def verify(self, reference: str) -> dict:
        return {"status": "success", "reference": reference, "amount_kobo": None, "currency": "NGN"}

    def refund(self, reference: str, amount: float) -> dict:
        if not reference:
            return {"status": "failed", "reason": "no reference to refund"}
        return {"status": "success", "refund_reference": f"RFD-{uuid.uuid4().hex[:10]}"}


class PaystackGateway:
    """Real Paystack integration -- see module docstring for verification status."""

    def __init__(self):
        self.secret_key = os.environ["MAUMART_PAYSTACK_SECRET_KEY"]
        self.headers = {"Authorization": f"Bearer {self.secret_key}", "Content-Type": "application/json"}

    def charge(self, amount: float, method: str, idempotency_key: str, email: str = None, callback_url: str = None) -> dict:
        """Initialize step only: returns status "pending" + the hosted-checkout URL."""
        body = {
            "amount": to_kobo(amount),
            "email": email,
            "reference": idempotency_key,
            "currency": "NGN",
            "channels": self._channels_for(method),
        }
        if callback_url:
            body["callback_url"] = callback_url
        try:
            resp = requests.post(
                f"{paystack_base_url()}/transaction/initialize",
                headers=self.headers, json=body, timeout=HTTP_TIMEOUT,
            )
            data = resp.json()
        except (requests.RequestException, ValueError):
            logger.exception("Paystack initialize failed for reference=%s", idempotency_key)
            return {"status": "failed", "reference": None}
        if not data.get("status"):
            logger.warning("Paystack initialize rejected reference=%s message=%s", idempotency_key, data.get("message"))
            return {"status": "failed", "reference": None}
        return {
            "status": "pending",  # the real outcome arrives by webhook / verify
            "reference": data["data"].get("reference", idempotency_key),
            "authorization_url": data["data"]["authorization_url"],
        }

    def verify(self, reference: str) -> dict:
        """
        Returns status one of: success | pending | failed | error.
        "error" means we could not find out (network/API problem) -- callers must not
        treat it as a failed payment.
        """
        try:
            resp = requests.get(
                f"{paystack_base_url()}/transaction/verify/{reference}",
                headers=self.headers, timeout=HTTP_TIMEOUT,
            )
            if resp.status_code >= 500 or resp.status_code in (401, 403, 429):
                # Outage, rate limit or bad API key: we learned nothing about the payment.
                logger.error("Paystack verify HTTP %s for reference=%s", resp.status_code, reference)
                return {"status": "error", "reference": reference}
            data = resp.json()
        except (requests.RequestException, ValueError):
            logger.exception("Paystack verify failed for reference=%s", reference)
            return {"status": "error", "reference": reference}
        if not data.get("status"):
            # Paystack answers an unknown reference with status=false; that is "not paid", not an outage.
            return {"status": "failed", "reference": reference}
        d = data["data"]
        raw = d.get("status")
        if raw == "success":
            status = "success"
        elif raw in ("pending", "ongoing", "processing", "queued"):
            status = "pending"
        else:  # failed, abandoned, reversed, ...
            status = "failed"
        return {"status": status, "reference": reference, "amount_kobo": d.get("amount"), "currency": d.get("currency")}

    def refund(self, reference: str, amount: float) -> dict:
        try:
            resp = requests.post(
                f"{paystack_base_url()}/refund",
                headers=self.headers, json={"transaction": reference, "amount": to_kobo(amount)},
                timeout=HTTP_TIMEOUT,
            )
            data = resp.json()
        except (requests.RequestException, ValueError):
            logger.exception("Paystack refund failed for reference=%s", reference)
            return {"status": "failed", "reason": "gateway unreachable"}
        if data.get("status"):
            return {"status": "success", "refund_reference": data["data"].get("id")}
        return {"status": "failed", "reason": data.get("message", "unknown error")}

    @staticmethod
    def _channels_for(method: str) -> list[str]:
        return {
            "card": ["card"],
            "bank_transfer": ["bank_transfer"],
            "ussd": ["ussd"],
        }.get(method, ["card", "bank_transfer", "ussd"])


_gateway = None


def is_mock() -> bool:
    return os.environ.get("MAUMART_PAYMENT_MOCK", "true").strip().lower() != "false"


def webhook_secret() -> str:
    return os.environ.get("MAUMART_PAYSTACK_SECRET_KEY", "")


def _get_gateway():
    global _gateway
    if _gateway is not None:
        return _gateway
    _gateway = MockGateway() if is_mock() else PaystackGateway()
    return _gateway


def reset_gateway_cache():
    """Test hook -- forces _get_gateway() to re-read env vars on next call."""
    global _gateway
    _gateway = None


def charge(amount: float, method: str, idempotency_key: str, email: str = None, callback_url: str = None) -> dict:
    return _get_gateway().charge(amount, method, idempotency_key, email=email, callback_url=callback_url)


def verify(reference: str) -> dict:
    return _get_gateway().verify(reference)


def refund(reference: str, amount: float) -> dict:
    return _get_gateway().refund(reference, amount)
