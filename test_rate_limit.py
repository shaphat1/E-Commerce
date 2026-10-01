"""
Demonstrates the rate limiter (backend/rate_limit.py) actually blocks
excessive attempts. Kept separate from tests/test_api.py deliberately:
this test exhausts the /auth/login bucket for 127.0.0.1 by design, which
would make a subsequent run of the main suite (sharing the same
long-running server process) report spurious 429s. Restart the server
before running the main suite again after this one.

Each attempt uses a DIFFERENT email, so this exercises the per-IP limiter on its own; the
separate per-account lockout (10 failures per email) is covered in tests/test_hardening.py.

Run: python tests/test_rate_limit.py   (against a freshly started server)
"""
import sys
import os
import uuid
import requests

BASE = os.environ.get("MAUMART_TEST_BASE", "http://127.0.0.1:8000")

MAX_ATTEMPTS = 20  # matches rate_limit(20, 300) in routers/auth.py
statuses = []

for i in range(MAX_ATTEMPTS + 3):
    r = requests.post(f"{BASE}/auth/login", json={"email": f"nobody.{uuid.uuid4().hex[:8]}@maumart.ng", "password": "wrong"})
    statuses.append(r.status_code)

ok_401_count = statuses[:MAX_ATTEMPTS].count(401)
blocked_count = statuses[MAX_ATTEMPTS:].count(429)

print(f"First {MAX_ATTEMPTS} attempts -> 401 (invalid credentials): {ok_401_count}/{MAX_ATTEMPTS}")
print(f"Next 3 attempts (over the limit) -> 429 (rate limited): {blocked_count}/3")
print(f"Full status sequence: {statuses}")

passed = ok_401_count == MAX_ATTEMPTS and blocked_count == 3
print("\nPASS" if passed else "\nFAIL")
sys.exit(0 if passed else 1)
