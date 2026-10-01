"""
Concurrency acceptance test (assessment item P0-1): overselling.

Several buyers check out at the same instant for the LAST unit of a listing.
Exactly one must succeed, the rest must get HTTP 400 (not enough stock),
final stock must be exactly 0 (never negative), and exactly one order for
that listing may exist in a paid state.

Needs a running backend with the demo seed loaded (see README), because it
uses the seeded vendor and buyer accounts.

Run: python tests/test_concurrency.py        (from backend/)
     MAUMART_TEST_BASE=http://127.0.0.1:8001 python tests/test_concurrency.py
"""
import os
import sys
import threading
import uuid

import requests

BASE = os.environ.get("MAUMART_TEST_BASE", "http://127.0.0.1:8000")
BUYERS = [
    ("amina.sule@maumart.ng", "BuyerPass1"),
    ("emeka.nwosu@maumart.ng", "BuyerPass1"),
    ("ruth.philemon@maumart.ng", "BuyerPass1"),
]
TRIALS = int(os.environ.get("MAUMART_RACE_TRIALS", "3"))


def login(email, password):
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": password})
    r.raise_for_status()
    return r.json()["token"]


def h(token):
    return {"Authorization": f"Bearer {token}"}


def main():
    vendor_token = login("ibrahim.books@maumart.ng", "VendorPass1")
    buyer_tokens = [login(e, p) for e, p in BUYERS]

    failures = []
    for trial in range(1, TRIALS + 1):
        r = requests.post(f"{BASE}/listings", headers=h(vendor_token), json={
            "title": f"Race item {uuid.uuid4().hex[:6]}", "category": "Books & Study Materials",
            "description": "one left", "price": 1000, "quantity": 1,
            "photo_urls": ["https://picsum.photos/seed/race/400"],
        })
        r.raise_for_status()
        listing_id = r.json()["id"]

        barrier = threading.Barrier(len(buyer_tokens))
        statuses = [None] * len(buyer_tokens)

        def attempt(i):
            barrier.wait()
            resp = requests.post(f"{BASE}/cart/checkout", headers=h(buyer_tokens[i]), json={
                "items": [{"listing_id": listing_id, "quantity": 1}],
                "delivery_address": "MAU Hostel", "payment_method": "pay_on_delivery",
            })
            statuses[i] = resp.status_code

        threads = [threading.Thread(target=attempt, args=(i,)) for i in range(len(buyer_tokens))]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        stock = requests.get(f"{BASE}/listings/{listing_id}").json()["quantity"]
        ok = statuses.count(200)
        rejected = statuses.count(400)
        good = ok == 1 and rejected == len(buyer_tokens) - 1 and stock == 0
        print(f"trial {trial}: statuses={statuses} final_stock={stock} -> {'PASS' if good else 'FAIL'}")
        if not good:
            failures.append(trial)

    if failures:
        print(f"\nFAILED trials: {failures}")
        sys.exit(1)
    print(f"\nAll {TRIALS} trials passed: exactly one buyer got the last unit, stock never went negative.")


if __name__ == "__main__":
    main()
