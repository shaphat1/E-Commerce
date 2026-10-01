"""
Hardening checks, self-contained (starts its own throwaway backends on ports 8071/8072).

  * production mode refuses unsafe configuration (mock payments, console email, SQLite, wildcard CORS)
  * two API instances sharing one database agree on sessions and rate limits (horizontal scaling)
  * stored XSS through a listing title cannot break out of the storefront's JSON-LD block
  * per-account login lockout works even when requests come from "different" clients
  * unapproved (pending-review) listings are not publicly readable
  * over-long passwords give 422, not a 500

Run: python tests/test_hardening.py        (from backend/)
"""
import os
import subprocess
import sys
import tempfile
import time
import uuid

import requests

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A, B = "http://127.0.0.1:8071", "http://127.0.0.1:8072"
results = []


def record(name, ok, detail=""):
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  -> {detail}"))


def start(port, env):
    p = subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--port", str(port)],
                         cwd=BACKEND_DIR, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        try:
            if requests.get(f"http://127.0.0.1:{port}/healthz", timeout=1).ok:
                return p
        except requests.RequestException:
            time.sleep(0.25)
    p.terminate()
    raise RuntimeError(f"server on {port} did not start")


pilot_procs = []


def _stop(procs):
    for p in procs:
        p.terminate()
    procs.clear()


def start_pilot(db_file, penv):
    """A production-mode instance on the same temp database. Production forbids SQLite, so we
    bypass only that one check via a tiny launcher that stubs config.validate for the DB rule."""
    launcher = (
        "import os, config\n"
        "orig = os.environ['DATABASE_URL']\n"
        "os.environ['DATABASE_URL'] = 'postgresql://stub'\n"
        "config.validate_production_config()\n"
        "os.environ['DATABASE_URL'] = orig\n"
        "config.validate_production_config = lambda: []\n"
        "import uvicorn; uvicorn.run('main:app', port=8073)\n"
    )
    penv = {**penv, "DATABASE_URL": f"sqlite:///{db_file}"}
    p = subprocess.Popen([sys.executable, "-c", launcher], cwd=BACKEND_DIR, env=penv,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    pilot_procs.append(p)
    for _ in range(60):
        try:
            if requests.get("http://127.0.0.1:8073/healthz", timeout=1).ok:
                return "http://127.0.0.1:8073"
        except requests.RequestException:
            time.sleep(0.25)
    raise RuntimeError("pilot server did not start")


def prod_validation():
    base = {k: v for k, v in os.environ.items() if not k.startswith("MAUMART_") and k != "DATABASE_URL"}
    code = "import config; config.validate_production_config(); print('BOOT-OK')"

    def run(extra):
        return subprocess.run([sys.executable, "-c", code], cwd=BACKEND_DIR, env={**base, **extra},
                              capture_output=True, text=True)

    r = run({"MAUMART_ENV": "production"})
    record("production refuses a default (dev) configuration", r.returncode != 0 and "Refusing to start" in r.stderr)
    for needle in ("MAUMART_PAYMENT_MOCK", "MAUMART_NOTIFY_BACKEND", "DATABASE_URL", "MAUMART_ALLOWED_ORIGINS"):
        record(f"  ...and names {needle}", needle in r.stderr)
    good = {"MAUMART_ENV": "production", "DATABASE_URL": "postgresql://u:p@db/x", "MAUMART_ALLOWED_ORIGINS": "https://app.example.ng",
            "MAUMART_PAYMENT_MOCK": "false", "MAUMART_PAYSTACK_SECRET_KEY": "sk_live_x",
            "MAUMART_NOTIFY_BACKEND": "smtp", "MAUMART_SMTP_HOST": "smtp.example.ng", "MAUMART_APP_URL": "https://app.example.ng"}
    r = run(good)
    record("production boots with a correct configuration", r.returncode == 0 and "BOOT-OK" in r.stdout, r.stderr[-300:])
    pilot = {k: v for k, v in good.items() if k != "MAUMART_PAYSTACK_SECRET_KEY"}
    r = run({**pilot, "MAUMART_PAYMENT_MOCK": "true"})
    record("production + mock payments is refused", r.returncode != 0 and "MAUMART_PILOT_COD_ONLY" in r.stderr)
    r = run({**pilot, "MAUMART_PAYMENT_MOCK": "true", "MAUMART_PILOT_COD_ONLY": "1"})
    record("production + mock boots only with the explicit COD-only pilot switch", r.returncode == 0, r.stderr[-200:])
    r = run({**good, "MAUMART_ALLOWED_ORIGINS": "*"})
    record("production refuses wildcard CORS", r.returncode != 0)
    r = subprocess.run([sys.executable, "seed.py"], cwd=BACKEND_DIR, env={**base, "MAUMART_ENV": "production"}, capture_output=True, text=True)
    record("seed.py refuses to run in production", r.returncode != 0 and "Refusing" in (r.stderr + r.stdout))


def main():
    prod_validation()

    db_file = os.path.join(tempfile.mkdtemp(), "hard.db")
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{db_file}", "MAUMART_ENV": "development"}
    subprocess.run([sys.executable, "seed.py"], cwd=BACKEND_DIR, env=env, check=True, capture_output=True)
    pa, pb = start(8071, env), start(8072, env)
    try:
        # --- multi-instance
        tok = requests.post(f"{A}/auth/login", json={"email": "amina.sule@maumart.ng", "password": "BuyerPass1"}).json()["token"]
        me = requests.get(f"{B}/auth/me", headers={"Authorization": f"Bearer {tok}"})
        record("login on instance A is accepted by instance B", me.status_code == 200 and me.json()["email"] == "amina.sule@maumart.ng", me.text[:120])
        requests.post(f"{B}/auth/logout", headers={"Authorization": f"Bearer {tok}"})
        record("logout on B invalidates the session on A",
               requests.get(f"{A}/auth/me", headers={"Authorization": f"Bearer {tok}"}).status_code == 401)

        # --- per-account lockout, split across both instances
        codes = []
        for i in range(12):
            codes.append(requests.post(f"{(A, B)[i % 2]}/auth/login",
                                       json={"email": "emeka.nwosu@maumart.ng", "password": "WrongPass9"}).status_code)
        record("wrong passwords are throttled per account across instances (401s then 429)", 429 in codes and codes[0] == 401, str(codes))
        good = requests.post(f"{A}/auth/login", json={"email": "emeka.nwosu@maumart.ng", "password": "BuyerPass1"})
        record("locked account rejects even the right password until the window passes", good.status_code == 429, str(good.status_code))

        # --- XSS in JSON-LD
        vt = requests.post(f"{A}/auth/login", json={"email": "ibrahim.books@maumart.ng", "password": "VendorPass1"}).json()["token"]
        payload = "x</script><script>alert(1)</script>"
        r = requests.post(f"{A}/listings", headers={"Authorization": f"Bearer {vt}"}, json={
            "title": payload, "category": "Books & Study Materials", "description": payload,
            "price": 100, "quantity": 1, "photo_urls": ["https://picsum.photos/seed/x/400"]})
        lid = r.json()["id"]
        html = requests.get(f"{A}/store/product/{lid}").text
        record("listing title cannot close the JSON-LD <script> block", "</script><script>alert(1)" not in html and "<script>alert(1)" not in html)
        record("storefront sends a Content-Security-Policy header",
               "Content-Security-Policy" in requests.get(f"{A}/store/").headers)

        # --- pending-review listing is not public
        r = requests.post(f"{A}/listings", headers={"Authorization": f"Bearer {vt}"}, json={
            "title": "Restricted thing", "category": "Pharmacy & Health", "description": "d", "price": 100,
            "quantity": 1, "photo_urls": ["https://picsum.photos/seed/y/400"]})
        pid, st = r.json()["id"], r.json()["status"]
        record("restricted listing is created pending review", st == "pending_admin_review", st)
        record("pending listing is hidden from the public API and storefront",
               requests.get(f"{A}/listings/{pid}").status_code == 404 and requests.get(f"{A}/store/product/{pid}").status_code == 404)

        # --- over-long password
        r = requests.post(f"{A}/auth/register", json={"name": "Long", "email": f"l{uuid.uuid4().hex[:6]}@maumart.ng",
                          "phone": "+2348011122233", "password": "a1" * 60, "role": "buyer", "agreed_to_terms": True})
        record("over-long password is a 422, not a 500", r.status_code == 422, str(r.status_code))

        # --- pilot mode really blocks non-COD orders (separate production-mode instance)
        penv = {**env, "MAUMART_ENV": "production", "MAUMART_PAYMENT_MOCK": "true", "MAUMART_PILOT_COD_ONLY": "1",
                "MAUMART_NOTIFY_BACKEND": "smtp", "MAUMART_SMTP_HOST": "127.0.0.1", "MAUMART_ALLOWED_ORIGINS": "https://app.example.ng",
                "MAUMART_APP_URL": "https://app.example.ng"}

        pc = start_pilot(db_file, penv)
        try:
            t = requests.post(f"{pc}/auth/login", json={"email": "amina.sule@maumart.ng", "password": "BuyerPass1"}).json()["token"]
            lst = requests.get(f"{pc}/listings").json()[0]["id"]
            body = lambda m: {"items": [{"listing_id": lst, "quantity": 1}], "delivery_address": "MAU", "payment_method": m}
            card = requests.post(f"{pc}/cart/checkout", headers={"Authorization": f"Bearer {t}"}, json=body("card"))
            cod = requests.post(f"{pc}/cart/checkout", headers={"Authorization": f"Bearer {t}"}, json=body("pay_on_delivery"))
            record("pilot mode refuses card payment but accepts pay on delivery",
                   card.status_code == 400 and cod.status_code == 200, f"card={card.status_code} cod={cod.status_code}")
        finally:
            _stop(pilot_procs)

        # --- misc
        record("unknown category page is a 404", requests.get(f"{A}/store/category/Nope").status_code == 404)
        record("healthz reports database reachable", requests.get(f"{A}/healthz").json() == {"status": "ok"})
        record("CORS preflight does not allow arbitrary origins",
               "access-control-allow-origin" not in {k.lower() for k in requests.options(
                   f"{A}/listings", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"}).headers})
    finally:
        pa.terminate()
        pb.terminate()

    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
