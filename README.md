# MAUMart

A hybrid, multi-vendor marketplace for Modibbo Adama University, Yola --
built for the CSC 720 (Electronic Commerce Technologies) coursework
assignment. Full design rationale, feasibility study, SRS, algorithms,
flowcharts, pseudocode, and ERD/architecture are in the accompanying
report (`MAUMart_Coursework_Report.md`); this file covers running the
code and what's actually been verified versus what hasn't.

## Structure

```
backend/            FastAPI API: auth, catalog, cart/checkout, orders,
                     reviews, recommendations, admin, user data rights
  routers/storefront.py   Server-rendered public HTML storefront (SEO)
  templates/, static/     Jinja2 templates + CSS for the storefront
  notifications.py         Pluggable email backend (console / SMTP)
  order_service.py         Atomic stock reservation, idempotent confirm/release, expiry sweep
  payment_gateway.py       Mock gateway + Paystack client; routers/payments.py = webhook + verify
  config.py                Production fail-closed configuration checks
  scripts/                 Postgres backup/restore scripts
  tests/                   Real test suites -- see "Testing" below
frontend/           Flet client -- one codebase for Desktop, Web, Mobile
elicitation/        Real interview/questionnaire instruments
TERMS_OF_SERVICE.md, PRIVACY_POLICY.md, REFUND_POLICY.md,
VENDOR_AGREEMENT.md   Legal documents (coursework-quality drafts)
docker-compose.yml, backend/Dockerfile, frontend/Dockerfile
.github/workflows/ci.yml
```

## 1. Run the backend

```bash
cd backend
pip install -r requirements.txt
python seed.py          # DEV ONLY: wipes the DB and loads demo vendors/listings/buyers
uvicorn main:app --reload
```

The JSON API is at `http://127.0.0.1:8000` (docs at `/docs`, disabled in production). The
**server-rendered public storefront** is at `http://127.0.0.1:8000/store/`. `GET /healthz`
checks that the API can reach the database.

**Demo logins** (created by `seed.py`; never present in a production database):

| Role   | Email                        | Password    |
|--------|-------------------------------|-------------|
| Admin  | admin@maumart.ng             | AdminPass1  |
| Vendor | ibrahim.books@maumart.ng     | VendorPass1 |
| Buyer  | amina.sule@maumart.ng        | BuyerPass1  |

In production create the first administrator with `python create_admin.py <email> "<name>" <phone>`
instead. See **DEPLOYMENT.md** for the full production procedure and go-live checklist.

### Environment variables

Copy `.env.example` to `.env` for Docker Compose. `MAUMART_ENV=production` makes the backend
**refuse to start** on an unsafe configuration (mock payments, console email, SQLite, wildcard or
unset CORS origins).

| Variable | Default | Purpose |
|---|---|---|
| `MAUMART_ENV` | `development` | `production` enables fail-closed startup checks and hides `/docs` |
| `DATABASE_URL` | `sqlite:///./maumart.db` | `postgresql://...` for Postgres (required in production) |
| `MAUMART_ALLOWED_ORIGINS` | local Flet dev ports | Comma-separated CORS allow-list (required in production, no `*`) |
| `MAUMART_APP_URL` | `http://127.0.0.1:8551` | Where storefront "Open the app" links and the payment callback point |
| `MAUMART_NOTIFY_BACKEND` | `console` | `console` logs (including reset codes: dev only) or `smtp` (required in production) |
| `MAUMART_SMTP_HOST/PORT/USER/PASSWORD/FROM/TLS` | -- | Read when `MAUMART_NOTIFY_BACKEND=smtp` |
| `MAUMART_PAYMENT_MOCK` | `true` | `false` + `MAUMART_PAYSTACK_SECRET_KEY` for real Paystack (required in production) |
| `MAUMART_RESERVATION_MINUTES` | `30` | How long unpaid stock stays reserved on a live gateway |
| `MAUMART_SWEEP_INTERVAL` | `60` | Seconds between expiry sweeps |
| `MAUMART_PILOT_COD_ONLY` | off | `1` lets production run the mock gateway but accepts pay-on-delivery only |
| `MAUMART_ENABLE_HSTS` | off | Set to `1` once HTTPS works end to end |
| `FORWARDED_ALLOW_IPS` | `127.0.0.1` | Reverse-proxy address, so rate limiting sees real client IPs |
| `MAUMART_API_BASE` (frontend) | `http://127.0.0.1:8000` | Where the Flet client points its API calls |

## 2. Run the frontend

```bash
cd frontend
pip install -r requirements.txt
flet run main.py            # desktop window
# or
flet run main.py --web      # opens in your browser
```

Mobile packaging: `flet build apk` / `flet build ipa` (same code, a build
step, not a separate codebase).

## 3. SEO storefront

Flet renders web output through Flutter's web engine, which draws to
canvas rather than semantic HTML -- a search crawler sees essentially no
content on the Flet app. `backend/routers/storefront.py` serves the
public catalog (home, category, product, search) as real server-rendered
HTML with schema.org Product/Offer structured data, `robots.txt`, and a
dynamic `sitemap.xml`, alongside the JSON API on the same FastAPI
process. Verify it's actually crawlable yourself with `curl
http://127.0.0.1:8000/store/` -- no JavaScript execution needed to see
the content. Authenticated actions (login, cart, dashboards) link out to
the Flet app from every storefront page.

## 4. Database: SQLite (default) or real Postgres

SQLite needs no setup. To run against Postgres instead:

```bash
# once: create a database and user
sudo -u postgres psql -c "CREATE USER maumart WITH PASSWORD 'maumart_dev_pw';"
sudo -u postgres psql -c "CREATE DATABASE maumart OWNER maumart;"

export DATABASE_URL="postgresql://maumart:maumart_dev_pw@127.0.0.1:5432/maumart"
cd backend && MAUMART_SEED_CONFIRM=yes python seed.py && uvicorn main:app --reload   # seed.py drops all tables, hence the confirmation
```

This was verified end-to-end during development: seeded, ran the full
29-case test suite against it, and confirmed real full-text search
(`to_tsvector`/`plainto_tsquery`) returns correctly ranked results --
`listings.py`'s search branches on DB dialect specifically for this,
falling back to `ILIKE` on SQLite.

### Backup and restore (Postgres only)

```bash
DATABASE_URL=postgresql://... bash backend/scripts/backup_db.sh ./backups
DATABASE_URL=postgresql://... bash backend/scripts/restore_db.sh ./backups/maumart_backup_TIMESTAMP.dump
```

Actually tested during development: backed up a seeded database, dropped
its entire schema (simulated disaster), restored from the dump, and
confirmed every user and listing came back correctly.

## 5. Notifications

`backend/notifications.py` is a pluggable backend. `ConsoleNotificationBackend`
(default) logs instead of delivering -- normal for dev. `SMTPNotificationBackend`
is real `smtplib` code, protocol-verified against a local test SMTP server
(`backend/tests/test_notifications.py`) since this project's dev environment
had no route to a real mail relay. To use it for real:

```bash
export MAUMART_NOTIFY_BACKEND=smtp
export MAUMART_SMTP_HOST=smtp.yourprovider.com
export MAUMART_SMTP_PORT=587
export MAUMART_SMTP_USER=...
export MAUMART_SMTP_PASSWORD=...
```

## 6. Payments

Checkout reserves stock atomically **before** asking for money, then:

- **Mock gateway** (`MAUMART_PAYMENT_MOCK=true`, default): payment succeeds instantly and **moves no
  money**. Development and tests only; production refuses to start with it.
- **Live Paystack** (`MAUMART_PAYMENT_MOCK=false`): checkout returns orders in `pending_payment`
  with a `payment_url`; the buyer pays on Paystack's page; the order is confirmed by the
  signature-verified `POST /payments/webhook/paystack` or the buyer's `POST /payments/verify/{reference}`.
  Confirmation is idempotent and checks the paid amount against the order total. Unpaid
  reservations expire (default 30 min) and the stock is returned; a payment that arrives after
  expiry is honoured if stock remains, otherwise an admin refund dispute is opened automatically.
- **Pay on delivery** never touches the gateway.

**What is and is not verified:** the whole flow above is tested end to end
(`tests/test_payment_flow.py`) against a local stub of Paystack's HTTP API. **It has never been run
against api.paystack.co.** Before taking real money, complete one payment in Paystack *test mode*
and confirm the webhook arrives and is accepted (DEPLOYMENT.md, step 7).

Refunds (`POST /admin/disputes/{id}/resolve`) call the gateway and set a real `refunded` status.
Cash-on-delivery refunds are settled offline. A dispute can only be resolved once.

## 7. TLS / HTTPS

Not enabled by default (plain HTTP, matching most reverse-proxy-terminated
deployments). To run the backend over TLS directly with a local dev cert:

```bash
openssl req -x509 -newkey rsa:2048 -keyout backend/certs/key.pem \
  -out backend/certs/cert.pem -days 365 -nodes -subj "/CN=127.0.0.1"
cd backend
uvicorn main:app --host 127.0.0.1 --port 8443 \
  --ssl-keyfile certs/key.pem --ssl-certfile certs/cert.pem
```

Verified during development: real HTTPS served, plain HTTP on the same
port refused, certificate inspectable via `openssl s_client`. A real
production deployment would terminate TLS at a reverse proxy with a
CA-signed cert (Let's Encrypt, etc.) rather than serving a self-signed
cert directly -- this is a local-dev proof that the mechanism works, not
a deployment recommendation.

## 8. Docker

```bash
cp .env.example .env            # set POSTGRES_PASSWORD at minimum
docker compose up --build       # Postgres + API (:8000) + Flet web client (:8551)
docker compose --profile demo run --rm seed   # optional, DESTRUCTIVE: loads demo data
```

The database is not published to the host, and the stack no longer seeds (wipes) the database on
start. **Not yet executed by the author** (no Docker daemon in the development environment); the CI
`docker` job builds and starts it on every push, so treat the first run as its first test.

## 9. CI

`.github/workflows/ci.yml` runs on every push/PR to `main`: the API suite, overselling race,
accessibility and performance checks on **both SQLite and PostgreSQL**; the live-gateway payment
flow and hardening suites; the frontend smoke test; and a Docker build + `docker compose up`
health check. **It has not yet executed on GitHub's runners**, so the first push is its first run.

## 10. Testing

Run from `backend/` (`pip install -r requirements-dev.txt` first):

```bash
python seed.py && uvicorn main:app &       # DEV database; suites below share this server

MAUMART_SERVER_LOG=/path/to/server.log python tests/test_api.py   # 29 cases (reads reset/verify codes from the log)
python tests/test_concurrency.py     # N buyers, 1 unit: exactly one succeeds, stock never negative
python tests/test_accessibility.py   # static checks on the SSR storefront
MAUMART_PERF_CONFIRM=yes python tests/test_performance.py   # loads 5,000 orders; WRITES to the DB
python tests/test_rate_limit.py      # run against a FRESH server (exhausts the login bucket)
python tests/test_payment_gateway.py # webhook signature unit tests
python tests/test_notifications.py   # SMTP backend against a local test server

# self-contained (start their own servers / temp databases):
python tests/test_payment_flow.py    # live gateway flow against a Paystack stub
python tests/test_hardening.py       # prod config, multi-instance sessions, XSS, lockout

cd ../frontend && python smoke_test.py   # builds all 11 screens against the live backend
```

Last full run (development machine, single core): every suite above passes on SQLite and on
PostgreSQL 16, including the overselling race (3/3 trials, one winner each), 40 concurrent
recommendation requests (p95 about 330 ms with 5,000 orders, previously 0 of 20 completing within
60 s) and 50 browse requests under 10 concurrent users (p95 about 90 ms).

## 11. Elicitation

`elicitation/Elicitation_Instruments.md` -- real interview guides,
a student questionnaire, an observation checklist, and an institutional
stakeholder guide, to replace the reasoned baseline in the report's
Section 3 with actual primary research.

## Known gaps (what "deployment ready" does and does not mean)

Fixed since the readiness assessment: overselling, recommendation and browse scaling, live
payment flow, in-process sessions/rate limits (now in the database, so multiple instances agree).
See `CHANGES.md` for the full list with evidence.

Still open, and not something code in this repository can close:

- **Live Paystack has not been exercised against Paystack itself** (stub only). One test-mode
  payment is required before real money.
- **Docker and CI have not run on real infrastructure** yet.
- **Legal documents are drafts** with unresolved `[...]` placeholders and have had no legal review;
  no data-protection impact assessment has been done.
- **No penetration test** and no Flet-dashboard accessibility test with assistive technology.
- **Schema migrations:** tables are created with `create_all`, which never alters existing tables.
  Adopt Alembic before the first schema change to a database holding real data.
- **Email verification is not enforced** anywhere (the mechanism works; decide what it should gate).
- **No admin audit log**, no 2FA, no scheduled/monitored backups, no metrics or alerting.
- **Account lockout is a trade-off:** 10 failed logins lock that account for 15 minutes, which also
  lets someone deliberately lock a victim out. IP limits still apply on top.
- The Flet web client is served with `flet run --web`; put TLS and a reverse proxy in front of it.
- The elicitation instruments were never run, so requirements still rest on inference.
