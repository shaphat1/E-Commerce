"""
Live-gateway payment flow, end to end, against a LOCAL STUB of Paystack's HTTP API.

This proves OUR side of the integration: pending state, signature-verified webhook,
idempotent confirmation, amount check, verify fallback, reservation expiry, and
late-payment recovery. It does NOT prove Paystack's real API behaves like the stub --
that still needs one manual run in Paystack TEST mode (see DEPLOYMENT.md).

The test starts its own backend (port 8077) with MAUMART_PAYMENT_MOCK=false and a throwaway
SQLite database, so it needs no setup beyond `pip install -r requirements-dev.txt`.

Run: python tests/test_payment_flow.py        (from backend/)
"""
import hashlib
import hmac
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

SECRET = "sk_test_stub_secret"
STUB_PORT, API_PORT = 8078, 8077
API = f"http://127.0.0.1:{API_PORT}"
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# reference -> {"status": "success"|"abandoned"|..., "amount": kobo}
STUB_TX: dict[str, dict] = {}
STUB_DOWN = {"value": False}
results = []


def record(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  -> {detail}" if not ok else ""))


class PaystackStub(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n) or b"{}")
        if self.headers.get("Authorization") != f"Bearer {SECRET}":
            return self._send({"status": False, "message": "Invalid key"}, 401)
        if self.path == "/transaction/initialize":
            if not body.get("email"):
                return self._send({"status": False, "message": "Email is required"}, 400)
            STUB_TX[body["reference"]] = {"status": "abandoned", "amount": body["amount"]}
            return self._send({"status": True, "data": {
                "authorization_url": f"https://checkout.stub/{body['reference']}",
                "reference": body["reference"]}})
        if self.path == "/refund":
            return self._send({"status": True, "data": {"id": 987}})
        self._send({"status": False}, 404)

    def do_GET(self):
        if STUB_DOWN["value"]:
            return self._send({"message": "down"}, 503)
        if self.path.startswith("/transaction/verify/"):
            ref = self.path.rsplit("/", 1)[1]
            tx = STUB_TX.get(ref)
            if not tx:
                return self._send({"status": False, "message": "Transaction reference not found"}, 404)
            return self._send({"status": True, "data": {"status": tx["status"], "amount": tx["amount"], "currency": "NGN"}})
        self._send({"status": False}, 404)


def h(t):
    return {"Authorization": f"Bearer {t}"}


def sign(raw: bytes) -> str:
    return hmac.new(SECRET.encode(), raw, hashlib.sha512).hexdigest()


def webhook(reference, amount_kobo, event="charge.success", signature=None, raw=None):
    payload = raw if raw is not None else json.dumps(
        {"event": event, "data": {"reference": reference, "status": "success", "amount": amount_kobo, "currency": "NGN"}}
    ).encode()
    return requests.post(f"{API}/payments/webhook/paystack", data=payload, headers={
        "x-paystack-signature": signature if signature is not None else sign(payload),
        "Content-Type": "application/json"})


def register(label):
    s = uuid.uuid4().hex[:8]
    r = requests.post(f"{API}/auth/register", json={
        "name": label, "email": f"{label}.{s}@maumart.ng", "phone": f"+234{int(s, 16) % 10**9:09d}0",
        "password": "TestPass123", "role": "buyer", "agreed_to_terms": True})
    r.raise_for_status()
    return r.json()["token"]


def main():
    db_file = os.path.join(tempfile.mkdtemp(), "flow.db")
    env = dict(os.environ, DATABASE_URL=f"sqlite:///{db_file}", MAUMART_PAYMENT_MOCK="false",
               MAUMART_PAYSTACK_SECRET_KEY=SECRET, MAUMART_PAYSTACK_BASE_URL=f"http://127.0.0.1:{STUB_PORT}",
               MAUMART_SWEEP_INTERVAL="1", MAUMART_RESERVATION_MINUTES="30", MAUMART_ENV="development")
    stub = HTTPServer(("127.0.0.1", STUB_PORT), PaystackStub)
    threading.Thread(target=stub.serve_forever, daemon=True).start()

    subprocess.run([sys.executable, "seed.py"], cwd=BACKEND_DIR, env=env, check=True, capture_output=True)
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--port", str(API_PORT)],
                              cwd=BACKEND_DIR, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(40):
            try:
                if requests.get(f"{API}/healthz", timeout=1).ok:
                    break
            except requests.RequestException:
                time.sleep(0.25)
        run_checks(db_file, env)
    finally:
        server.terminate()
        stub.shutdown()

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    sys.exit(1 if failed else 0)


def run_checks(db_file, env):
    vendor_t = requests.post(f"{API}/auth/login", json={"email": "ibrahim.books@maumart.ng", "password": "VendorPass1"}).json()["token"]
    buyer_t = register("payer")
    other_t = register("other")

    def new_listing(qty):
        r = requests.post(f"{API}/listings", headers=h(vendor_t), json={
            "title": f"Item {uuid.uuid4().hex[:6]}", "category": "Books & Study Materials", "description": "d",
            "price": 1000, "quantity": qty, "photo_urls": ["https://picsum.photos/seed/x/400"]})
        r.raise_for_status()
        return r.json()["id"]

    def stock(lid):
        return requests.get(f"{API}/listings/{lid}").json()["quantity"]

    def checkout(token, lid, qty=1, method="card"):
        return requests.post(f"{API}/cart/checkout", headers=h(token), json={
            "items": [{"listing_id": lid, "quantity": qty}], "delivery_address": "MAU", "payment_method": method})

    # 1. Live checkout returns PENDING + payment URL, and reserves stock immediately.
    lid = new_listing(5)
    r = checkout(buyer_t, lid, 2)
    o = r.json()[0] if r.ok else {}
    record("checkout returns pending_payment with a payment_url", r.status_code == 200 and o.get("status") == "pending_payment"
           and str(o.get("payment_url", "")).startswith("https://checkout.stub/"), f"{r.status_code} {r.text[:200]}")
    record("stock is reserved before payment is confirmed", stock(lid) == 3, f"stock={stock(lid)}")
    ref, total_kobo = o.get("payment_reference"), int(round(o.get("total", 0) * 100))

    # 2. Webhook security.
    record("webhook with no/invalid signature is rejected (401)",
           webhook(ref, total_kobo, signature="deadbeef").status_code == 401)
    record("webhook with a tampered body is rejected (401)",
           webhook(ref, total_kobo, signature=sign(b"something else")).status_code == 401)
    mine = requests.get(f"{API}/orders/mine", headers=h(buyer_t)).json()
    record("rejected webhooks did not confirm the order", all(x["status"] == "pending_payment" for x in mine if x["id"] == o["id"]))

    # 3. Wrong amount is not trusted even when correctly signed.
    wr = webhook(ref, total_kobo - 100)
    mine = requests.get(f"{API}/orders/mine", headers=h(buyer_t)).json()
    record("signed webhook with the WRONG amount does not confirm", wr.ok and wr.json().get("amount_mismatch") is True
           and [x for x in mine if x["id"] == o["id"]][0]["status"] == "pending_payment", wr.text[:200])

    # 4. Valid webhook confirms; replay changes nothing.
    wr = webhook(ref, total_kobo)
    mine = requests.get(f"{API}/orders/mine", headers=h(buyer_t)).json()
    record("valid webhook confirms the order", wr.ok and [x for x in mine if x["id"] == o["id"]][0]["status"] == "confirmed_paid", wr.text[:200])
    before = stock(lid)
    for _ in range(3):
        webhook(ref, total_kobo)
    record("replayed webhooks are no-ops (stock and status unchanged)", stock(lid) == before == 3
           and [x for x in requests.get(f"{API}/orders/mine", headers=h(buyer_t)).json() if x["id"] == o["id"]][0]["status"] == "confirmed_paid")

    # 5. Verify fallback (webhook never arrives).
    lid2 = new_listing(3)
    o2 = checkout(buyer_t, lid2).json()[0]
    v = requests.post(f"{API}/payments/verify/{o2['payment_reference']}", headers=h(buyer_t))
    record("verify while still unpaid leaves the order pending", v.ok and v.json()[0]["status"] == "pending_payment", v.text[:200])
    STUB_TX[o2["payment_reference"]]["status"] = "success"
    v = requests.post(f"{API}/payments/verify/{o2['payment_reference']}", headers=h(buyer_t))
    record("verify after payment confirms the order", v.ok and v.json()[0]["status"] == "confirmed_paid", v.text[:200])
    record("another user cannot verify someone else's payment",
           requests.post(f"{API}/payments/verify/{o2['payment_reference']}", headers=h(other_t)).status_code == 404)

    # 6. Gateway outage during verify is reported, not treated as 'payment failed'.
    lid3 = new_listing(3)
    o3 = checkout(buyer_t, lid3).json()[0]
    STUB_DOWN["value"] = True
    v = requests.post(f"{API}/payments/verify/{o3['payment_reference']}", headers=h(buyer_t))
    STUB_DOWN["value"] = False
    record("gateway outage during verify -> 502, order untouched", v.status_code == 502
           and [x for x in requests.get(f"{API}/orders/mine", headers=h(buyer_t)).json() if x["id"] == o3["id"]][0]["status"] == "pending_payment", f"{v.status_code}")

    # 7. Buyer cancels an unpaid order -> stock returns; cannot cancel twice.
    c = requests.post(f"{API}/orders/{o3['id']}/cancel", headers=h(buyer_t))
    record("cancelling an unpaid order returns the reserved stock", c.ok and stock(lid3) == 3, f"{c.status_code} stock={stock(lid3)}")
    record("cancelling twice is rejected and does not double-restore stock",
           requests.post(f"{API}/orders/{o3['id']}/cancel", headers=h(buyer_t)).status_code == 400 and stock(lid3) == 3)

    # 8. Vendors cannot mark an unpaid order paid.
    lid4 = new_listing(2)
    o4 = checkout(buyer_t, lid4).json()[0]
    vr = requests.patch(f"{API}/orders/{o4['id']}/status", headers=h(vendor_t), json={"new_status": "confirmed_paid"})
    record("vendor cannot force an unpaid order to confirmed_paid", vr.status_code == 400, f"{vr.status_code}")

    # 9. Reservation expiry returns stock (sweeper), expired-but-unpaid.
    import sqlite3
    con = sqlite3.connect(db_file)
    con.execute("UPDATE orders SET expires_at = datetime('now', '-1 minute') WHERE id = ?", (o4["id"],))
    con.commit()
    for _ in range(20):
        time.sleep(0.5)
        if stock(lid4) == 2:
            break
    st = [x for x in requests.get(f"{API}/orders/mine", headers=h(buyer_t)).json() if x["id"] == o4["id"]][0]["status"]
    record("expired unpaid reservation is released by the sweeper", stock(lid4) == 2 and st == "payment_failed", f"stock={stock(lid4)} status={st}")

    # 10. Late payment for a released order, stock still available -> recovered.
    webhook(o4["payment_reference"], int(round(o4["total"] * 100)))
    st = [x for x in requests.get(f"{API}/orders/mine", headers=h(buyer_t)).json() if x["id"] == o4["id"]][0]["status"]
    record("late payment with stock available re-reserves and confirms", st == "confirmed_paid" and stock(lid4) == 1, f"status={st} stock={stock(lid4)}")

    # 11. Late payment when someone else took the last unit -> refund dispute opened.
    lid5 = new_listing(1)
    o5 = checkout(buyer_t, lid5).json()[0]
    requests.post(f"{API}/orders/{o5['id']}/cancel", headers=h(buyer_t))       # frees the unit
    taken = checkout(other_t, lid5)                                             # someone else buys it
    STUB_TX[taken.json()[0]["payment_reference"]]["status"] = "success"
    webhook(taken.json()[0]["payment_reference"], int(round(taken.json()[0]["total"] * 100)))
    webhook(o5["payment_reference"], int(round(o5["total"] * 100)))             # first buyer's money arrives late
    admin_t = requests.post(f"{API}/auth/login", json={"email": "admin@maumart.ng", "password": "AdminPass1"}).json()["token"]
    disputes = requests.get(f"{API}/admin/disputes", headers=h(admin_t)).json()
    record("late payment with no stock left opens an admin refund dispute and never oversells",
           any(d["order_id"] == o5["id"] for d in disputes) and stock(lid5) == 0,
           f"stock={stock(lid5)} disputes={len(disputes)}")

    # 12. Cash on delivery never touches the gateway even in live mode.
    lid6 = new_listing(2)
    cod = checkout(buyer_t, lid6, 1, "pay_on_delivery")
    record("pay_on_delivery confirms immediately without the gateway", cod.ok and cod.json()[0]["status"] == "confirmed_paid"
           and cod.json()[0]["payment_url"] is None, f"{cod.status_code} {cod.text[:150]}")

    # 13. Mock-only routes are hidden when mock is on is covered by test_api; here: unknown ref on verify.
    record("verify of an unknown reference is a 404",
           requests.post(f"{API}/payments/verify/nope", headers=h(buyer_t)).status_code == 404)


if __name__ == "__main__":
    main()
