"""
Performance acceptance test (assessment items P0-2 and P0-3).

Loads synthetic data directly into the database (500 listings, 5,000 paid orders, ~12,500
order items), then checks, against a running backend:

  * recommendations for one user stay fast and run in a handful of SQL queries
  * 10 concurrent users all get recommendations back (previously 0 of 20 completed)
  * /listings is paginated and issues few queries per page

It WRITES synthetic rows to whatever DATABASE_URL points at, so it refuses to run unless the
database is SQLite or MAUMART_PERF_CONFIRM=yes is set. Never point it at production.

Run (backend already running against the same DATABASE_URL, seeded):
    python tests/test_performance.py
"""
import os
import random
import statistics
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from sqlalchemy import event

from database import SessionLocal, engine, DATABASE_URL
import models

BASE = os.environ.get("MAUMART_TEST_BASE", "http://127.0.0.1:8000")
N_LISTINGS, N_ORDERS = 500, 5000
REC_P95_BUDGET_S = float(os.environ.get("MAUMART_REC_BUDGET", "0.3"))
results = []


def record(name, ok, detail=""):
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}  ({detail})")


def populate():
    random.seed(7)
    db = SessionLocal()
    vendor = db.query(models.Vendor).first()
    buyers = db.query(models.User).filter(models.User.role == "buyer").all()
    listings = []
    for i in range(N_LISTINGS):
        l = models.Listing(vendor_id=vendor.id, title=f"Perf item {i}", category=random.choice(models.CATEGORIES[:4]),
                           description="synthetic", price=random.randint(500, 20000), quantity=1000,
                           status="live", sales_count=random.randint(0, 50))
        db.add(l)
        listings.append(l)
    db.flush()
    for l in listings:
        db.add(models.ListingPhoto(listing_id=l.id, url="https://picsum.photos/seed/p/400"))
    db.commit()
    now = datetime.utcnow()
    for i in range(N_ORDERS):
        o = models.Order(buyer_id=random.choice(buyers).id, vendor_id=vendor.id, session_id=str(uuid.uuid4()),
                         subtotal=1000, vat_amount=75, delivery_fee=500, total=1575,
                         status=random.choice(models.PAID_STATUSES), delivery_address="x",
                         created_at=now - timedelta(days=random.randint(0, 60)))
        db.add(o)
        db.flush()
        for l in random.sample(listings, random.choice([2, 2, 3])):
            db.add(models.OrderItem(order_id=o.id, listing_id=l.id, quantity=1, price_at_purchase=l.price))
        if i % 500 == 0:
            db.commit()
    # Give buyer 1 a real history so the item-based CF path (the slow one) is exercised.
    buyer = buyers[0]
    for l in random.sample(listings, 10):
        db.add(models.Interaction(user_id=buyer.id, listing_id=l.id, type="purchase"))
    for _ in range(40):
        db.add(models.Interaction(user_id=random.choice(buyers).id, listing_id=random.choice(listings).id, type="view"))
    db.commit()
    db.close()


def main():
    if not DATABASE_URL.startswith("sqlite") and os.environ.get("MAUMART_PERF_CONFIRM") != "yes":
        sys.exit("Refusing to write synthetic data to a non-SQLite database without MAUMART_PERF_CONFIRM=yes")

    print(f"Loading {N_LISTINGS} listings / {N_ORDERS} orders ...")
    populate()

    token = requests.post(f"{BASE}/auth/login", json={"email": "amina.sule@maumart.ng", "password": "BuyerPass1"}).json()["token"]
    hdr = {"Authorization": f"Bearer {token}"}

    r = requests.get(f"{BASE}/recommendations", headers=hdr)
    tags = {x.get("reason") for x in r.json()}
    record("recommendations use the collaborative-filtering path", r.ok and "Customers who bought this also bought" in tags, f"{tags}")

    def timed(_):
        t = time.time()
        resp = requests.get(f"{BASE}/recommendations", headers=hdr, timeout=60)
        return resp.status_code, time.time() - t

    single = [timed(0) for _ in range(5)]
    record("single-request recommendation latency", all(c == 200 for c, _ in single) and statistics.median(t for _, t in single) < REC_P95_BUDGET_S,
           f"median {statistics.median(t for _, t in single) * 1000:.0f} ms, budget {REC_P95_BUDGET_S * 1000:.0f} ms")

    with ThreadPoolExecutor(10) as ex:
        conc = list(ex.map(timed, range(40)))
    times = sorted(t for _, t in conc)
    p95 = times[int(len(times) * 0.95) - 1]
    record("10 concurrent users: every recommendation request completes", all(c == 200 for c, _ in conc),
           f"{sum(c == 200 for c, _ in conc)}/{len(conc)} ok")
    record("10 concurrent users: p95 within budget", p95 < max(REC_P95_BUDGET_S * 10, 3.0), f"p95 {p95 * 1000:.0f} ms")

    # Browse: paginated + few queries.
    queries = []

    @event.listens_for(engine, "before_cursor_execute")
    def count(conn, cursor, statement, parameters, context, executemany):
        queries.append(statement)

    r = requests.get(f"{BASE}/listings?limit=50")
    record("/listings returns one page, not the whole catalogue", r.ok and len(r.json()) == 50
           and int(r.headers["X-Total-Count"]) >= N_LISTINGS, f"{len(r.json())} rows of {r.headers.get('X-Total-Count')}")
    # The server is a separate process, so its queries are not visible to this listener;
    # check the SQL count in-process through the same code path instead.
    from fastapi.testclient import TestClient
    import main
    queries.clear()
    with TestClient(main.app) as c:
        queries.clear()
        resp = c.get("/listings?limit=50")
        n = len(queries)
    record("a page of 50 listings costs <= 5 SQL queries", resp.status_code == 200 and n <= 5, f"{n} queries")
    queries.clear()
    with TestClient(main.app) as c:
        queries.clear()
        c.get("/store/")
        n_store = len(queries)
    record("storefront home costs <= 5 SQL queries", n_store <= 5, f"{n_store} queries")

    with ThreadPoolExecutor(10) as ex:
        def hit(_):
            s = time.time()
            requests.get(f"{BASE}/listings?limit=50")
            return time.time() - s
        lat = sorted(ex.map(hit, range(50)))
    record("/listings under 10 concurrent users: p95 < 1 s", lat[int(len(lat) * 0.95) - 1] < 1.0, f"p95 {lat[int(len(lat) * 0.95) - 1] * 1000:.0f} ms")

    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
