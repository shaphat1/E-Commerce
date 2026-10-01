# Deploying MAUMart

Read the **Known gaps** section of `README.md` first. In short: the code is ready for a supervised
pilot; a public launch taking real money also needs the items marked *external* below.

## Pilot vs. public launch

| | Supervised campus pilot | Public launch with real money |
|---|---|---|
| Payments | Pay on delivery, or mock gateway **only if no money is meant to move** | Live Paystack, tested in test mode first (step 7) |
| Legal docs | Placeholders filled in, reviewed informally | Reviewed and signed off (external) |
| Email | SMTP | SMTP |
| Everything else | Steps 1-6, 8-9 | All steps |

The backend will not start with `MAUMART_ENV=production` while the mock gateway is on, because the
mock marks every card payment "paid" without charging anyone. For a **cash-on-delivery-only pilot**
set `MAUMART_PILOT_COD_ONLY=1` (instead of Paystack settings): production then boots with the mock,
and checkout refuses every payment method except pay on delivery (tested). The app's payment
dropdown still lists the other methods; buyers who pick one see "Only pay on delivery is available".

## 1. Infrastructure

- A Linux host or container platform, PostgreSQL 16, and an SMTP provider.
- A reverse proxy (Caddy, nginx, a cloud load balancer) terminating HTTPS with a real certificate.
  The API serves plain HTTP behind it. The Flet client needs the same.
- Two public hostnames are typical: `api.example.ng` (backend) and `app.example.ng` (Flet client).

## 2. Configure (production)

Set these environment variables (see `.env.example`); startup fails with a list of everything wrong:

```
MAUMART_ENV=production
DATABASE_URL=postgresql://USER:PASS@HOST:5432/maumart
MAUMART_ALLOWED_ORIGINS=https://app.example.ng
MAUMART_APP_URL=https://app.example.ng
MAUMART_PAYMENT_MOCK=false
MAUMART_PAYSTACK_SECRET_KEY=sk_live_...        # sk_test_... for step 7
MAUMART_NOTIFY_BACKEND=smtp
MAUMART_SMTP_HOST=... MAUMART_SMTP_USER=... MAUMART_SMTP_PASSWORD=... MAUMART_SMTP_FROM=...
FORWARDED_ALLOW_IPS=<your reverse proxy's IP>
```

Keep secrets in your platform's secret store, not in the repository.

## 3. Start

```bash
docker compose up -d --build        # or run backend/Dockerfile on your platform
```

Tables are created on first start (guarded by a database lock, so several instances may boot at
once). Then create the first administrator (no demo data, no demo passwords):

```bash
docker compose exec backend python create_admin.py you@example.ng "Your Name" +2348012345678
```

Never run `seed.py` in production; it refuses to.

## 4. Scale out

Sessions, rate limits and stock reservations live in the database, so run as many API
instances as you need behind the load balancer (`WEB_CONCURRENCY` sets workers per instance). Each
instance runs a small background sweeper; it is idempotent, so that is safe.

## 5. HTTPS and headers

Once HTTPS works end to end, set `MAUMART_ENABLE_HSTS=1` and restart. Do not enable it earlier.

## 6. Backups

```bash
DATABASE_URL=postgresql://... bash backend/scripts/backup_db.sh ./backups
DATABASE_URL=postgresql://... bash backend/scripts/restore_db.sh ./backups/<file>.dump
```

Schedule the backup (cron / platform job), copy dumps off the host, and **test a restore on a spare
database** on a schedule. Nothing here is scheduled or monitored for you.

## 7. Paystack test-mode run (required before real money)

1. Use your Paystack **test** secret key and point a Paystack test webhook at
   `https://api.example.ng/payments/webhook/paystack`.
2. Place an order with the Card method, pay with a Paystack test card, and confirm: the order moves
   `pending_payment` to `confirmed_paid`, stock stays decremented once, and both emails send.
3. Re-send the webhook from Paystack's dashboard: nothing changes.
4. Abandon a payment and confirm the order is released after `MAUMART_RESERVATION_MINUTES`.
5. Refund one order from the admin dashboard and confirm it in Paystack.

This was only ever tested against a local stub, so do not skip it.

## 8. Go-live checklist

- [ ] Backend starts with `MAUMART_ENV=production` (it checks the items below for you)
- [ ] HTTPS valid on both hostnames; HSTS enabled
- [ ] `/healthz` monitored by an uptime checker; logs shipped somewhere (JSON lines on stdout)
- [ ] Backups scheduled, copied off-host, restore tested
- [ ] First admin created; no demo accounts exist (`select email from users`)
- [ ] Paystack test-mode run done; live key set
- [ ] Legal documents: every `[...]` placeholder replaced, reviewed (external)
- [ ] You decided what email verification should gate (it gates nothing today)
- [ ] An operator is watching for the first days (no alerting exists)

## 9. Before changing the database schema

`create_all` only creates missing tables. Introduce Alembic (generate an initial migration from the
current models) before the first schema change to a database that holds real data.
