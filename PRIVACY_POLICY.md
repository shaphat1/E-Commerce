# MAUMart Privacy Policy

*This is a coursework deliverable demonstrating an actual NDPA-compliant
privacy policy, not a substitute for legal review before any real deployment.
Placeholders below (marked `[...]`) would need real values before publication.*

**Last updated:** [date] · **Governing law:** Nigeria Data Protection Act (NDPA) 2023

## 1. Who this policy covers and who is responsible for your data

This policy covers everyone who uses MAUMart -- buyers, vendors, and
administrators. The **data controller** is `[MAUMart / Modibbo Adama
University ICT Directorate -- confirm the real institutional owner before
launch]`, contactable at `[privacy@maumart.ng or the real institutional
contact]`. Under NDPA 2023, you can also lodge a complaint with the
**Nigeria Data Protection Commission (NDPC)** if you believe your data has
been mishandled and MAUMart hasn't resolved it.

## 2. What we collect, and why

| Category | Examples | Why we process it | Lawful basis (NDPA 2023) |
|---|---|---|---|
| Account details | Name, email, phone, password (hashed) | Creating and securing your account | Necessary for the contract of using MAUMart |
| Vendor business details | Business name, category | Operating your storefront, buyer trust signals | Necessary for the contract |
| Delivery details | Delivery address per order | Fulfilling your orders | Necessary for the contract |
| Order & payment records | Items, totals, order status, payment method | Processing transactions, resolving disputes, tax/audit records | Necessary for the contract; legal obligation (financial record-keeping) |
| Browsing/interaction history | Product views, purchases (linked to your account) | Powering the "Recommended for you" feature | Legitimate interest, always overridable by you -- see Section 5 |
| Reviews | Rating, comment, linked to a completed order | Building vendor trust signals for other buyers | Legitimate interest (verified-purchase reviews only) |

We do **not** collect payment card details directly -- those go straight
to the payment gateway (Paystack/Flutterwave), which is a separate data
controller for that information under its own privacy policy.

## 3. Who we share data with

- **Payment gateway** (Paystack/Flutterwave): receives what's needed to
  process a payment. We never see or store your card number.
- **Vendors**: see your delivery address and order contents for orders
  placed with them -- nothing more.
- **MAUMart admins**: can see account and order data to resolve disputes,
  approve vendors, and moderate the platform.
- We do **not** sell personal data to third parties, and we do not share
  browsing/interaction history outside MAUMart.

## 4. How long we keep it

- **Order and review records** are retained for as long as needed for
  tax, audit, and dispute-resolution purposes, even after you delete
  your account (see Section 6) -- with your name, email, and phone
  scrubbed from the account itself at that point.
- **Recommendation interaction history** (views/purchases used for
  personalization) is kept only as long as your account is active, and
  you can clear it at any time without affecting your order history
  (Section 5).
- **Session tokens** expire automatically after 24 hours.

## 5. Your rights, and how to exercise them in-app

Under NDPA 2023, you have the right to:

- **Access** what we hold about you -- use **Privacy → Export my data**
  in the app, which returns your full profile, orders, reviews, and
  recommendation interaction history in one export.
- **Data portability** -- the same export is structured data you can
  take elsewhere.
- **Object to / restrict processing used for personalization** -- use
  **Privacy → Clear my recommendation history** to wipe the interaction
  log that powers "Recommended for you" without touching your order
  history. Your next visit starts from the trending/cold-start
  recommendations again.
- **Rectification** -- update your profile details in-app; contact
  `[support email]` for anything not editable directly.
- **Erasure** -- use **Privacy → Delete my account**. This immediately:
  anonymizes your name, email, and phone number; ends every active
  session; and makes your old password unusable. Order and review
  records tied to your account are **retained in anonymized form**
  rather than deleted outright, because MAUMart has a legal
  record-keeping obligation for completed transactions (tax/audit, and
  so vendors can still resolve a dispute on a past order). This is the
  same balance most e-commerce platforms strike between your erasure
  right and their legal retention duties.
- **Lodge a complaint** with the NDPC if you're unhappy with how a
  request was handled.

## 6. Security measures in place

Passwords are hashed (never stored in plain text); traffic is expected
to run over TLS in any real deployment; login/registration are rate-limited
against brute-force attempts; session tokens expire after 24 hours; and
dependencies are periodically scanned for known vulnerabilities. See the
project report's Testing Evidence section for how each of these was
verified, not just implemented.

## 7. Restricted-category products

Pharmacy & Health listings are limited to over-the-counter items and
require additional admin approval before going live -- this exists to
keep MAUMart out of regulated medication sales, not as a data-privacy
measure, but it's documented here because it affects what a Pharmacy
vendor's customers' order data can legitimately contain.

## 8. Children

MAUMart is built for the university community (students, staff) and is
not directed at children. We don't knowingly collect data from minors.

## 9. Changes to this policy

If this policy changes materially, users will be notified in-app before
the change takes effect.
