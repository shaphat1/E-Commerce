# Changes made to reach deployment readiness

Each item maps to the findings in the Deployment Readiness Assessment (1 Oct 2026). "Evidence" is a
test in `backend/tests/` that failed or could not run before and passes now.

## Assessment P0 -- defects that made real use unsafe

| Finding | Fix | Evidence |
|---|---|---|
| **Overselling:** 3 simultaneous buyers of 1 unit were all charged (stock -1) | Stock reserved with one atomic `UPDATE ... WHERE quantity >= n` *before* charging; DB `CHECK (quantity >= 0)`; idempotent confirm/release (`order_service.py`) | `test_concurrency.py`: original code failed 2/3 trials on SQLite and 3/3 on PostgreSQL; now exactly one winner in every trial on both |
| **Recommendations:** 6.8 s and 5,019 queries at 5,000 orders; 0/20 completed under load | One aggregate co-purchase query, bounded history, capped counts; also counts *all* paid statuses (it only counted `confirmed_paid`, so its data shrank as orders progressed) | `test_performance.py`: median well under 300 ms, 40/40 concurrent requests complete (p95 ~330 ms on a shared single core) |
| **Browse:** unpaginated, 507 queries for 500 rows | `limit`/`offset` (max 100) with `X-Total-Count`; eager-loaded vendor + photos; storefront pages paginated | `test_performance.py`: 3 queries per page of 50; p95 ~90 ms at 10 concurrent users |

## Assessment P1

| Finding | Fix | Evidence |
|---|---|---|
| Live payments rejected every payment; no webhook | Pending-order state, hosted-checkout URL, signature-verified idempotent webhook, verify fallback, amount check, reservation expiry + sweeper, late-payment recovery / auto refund dispute | `test_payment_flow.py` (20 checks, local Paystack stub) |
| Sessions, rate limits, idempotency in process memory | Sessions (token hash only) and rate-limit counters moved to the database; mock idempotency is dev-only | `test_hardening.py`: login on one instance accepted by another, lockout shared |
| Docker/CI never executed | Rewritten (see below); CI now builds and starts the stack | Not yet run on real infrastructure |

## Other defects found while fixing the above

- **Docker Compose seeded (wiped) the database on every container start.** Seeding is now opt-in, refuses production, and requires explicit confirmation on non-SQLite databases. `create_admin.py` added.
- **Backend image could not boot from requirements.txt:** `requests` and `jinja2` were missing (verified: `ModuleNotFoundError`); `psycopg2` was missing for Postgres. Fixed; dev/test deps split into `requirements-dev.txt`.
- **Frontend: admin "Mark resolved" always failed** (the API requires an explicit refund decision; the client sent none). Now "Refund buyer" / "Close, no refund".
- **Frontend: cart total omitted 7.5% VAT**, so buyers saw less than they were charged.
- **Stored XSS:** a vendor-chosen title containing `</script>` broke out of the storefront JSON-LD block. Escaped; storefront also sends a Content-Security-Policy.
- **Pending-review (e.g. pharmacy) and deactivated listings were publicly readable** by direct ID. Now 404.
- **Password reset code brute-forceable:** 6 digits, no attempt limit. Per-account limits added on reset codes and logins; unknown-email login timing equalised.
- **Passwords over 72 bytes caused HTTP 500** (bcrypt). Validated and rejected cleanly.
- Dispute resolution could be run twice (double refund); disputes could be opened on unpaid orders; vendors could mark unpaid orders paid; buyer cancel did not return stock; GMV counted only `confirmed_paid`; refunds of cash-on-delivery orders tried to call the gateway; cash on delivery would have started a real Paystack transaction in live mode; kobo conversion truncated (`int(19.99*100)`); gateway outage could strand reserved stock or be mistaken for a failed payment. All fixed and covered.
- Missing foreign-key indexes (Postgres does not add them), unique constraint on one-review-per-order, input length/URL/category validation, explicit CORS methods/headers, `docs` disabled in production, HSTS opt-in, `/healthz`, SMTP sends moved off the request thread, search `LIKE` wildcards escaped, templates path made absolute, HTTP timeouts and error handling in the Flet client.
- Fail-closed production configuration (`config.py`): refuses mock payments (unless the explicit COD-only pilot switch is set), console email, SQLite, wildcard/unset CORS.

## Unchanged by design (needs people, not code)

Legal review, Paystack test-mode run, real Docker/CI execution, penetration test, accessibility audit,
running the elicitation, schema migrations (Alembic), audit log, scheduled backups, alerting.
See `README.md` "Known gaps" and `DEPLOYMENT.md`.
