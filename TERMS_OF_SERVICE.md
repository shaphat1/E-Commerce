# MAUMart Terms of Service

*Coursework deliverable demonstrating what a real ToS needs to cover for
a Nigerian marketplace platform, referencing the Federal Competition and
Consumer Protection Act (FCCPA) 2018. Not a substitute for legal review
before real use. Placeholders marked `[...]`.*

**Last updated:** [date] · **Operator:** `[MAUMart / MAU ICT Directorate]`

## 1. Acceptance

By creating an account, you agree to these Terms, the [Privacy
Policy](PRIVACY_POLICY.md), and, if you register as a vendor, the
[Vendor Agreement](VENDOR_AGREEMENT.md). If you don't agree, don't use
MAUMart. Registration requires actively checking a box confirming this
-- silence or continued use isn't treated as agreement.

## 2. Who can use MAUMart

MAUMart is for members of the MAU community (students, staff) and
approved vendors serving them. You must be able to form a binding
contract under Nigerian law to use MAUMart. Accounts are personal --
don't share your login, and tell us immediately if you think someone
else has access to your account.

## 3. What MAUMart is (and isn't)

MAUMart is a **marketplace** connecting buyers and vendors. Except where
explicitly stated, **MAUMart is not the seller of record** for
vendor-listed items -- the vendor is. MAUMart facilitates discovery,
payment, and dispute handling, but the contract of sale for a given
order is between the buyer and that vendor. This matters for consumer
protection: under FCCPA 2018, the vendor carries primary responsibility
for product quality, accurate description, and fitness for purpose;
MAUMart's obligation is to provide a functioning platform and a fair
dispute-resolution process (see the [Refund & Return Policy](REFUND_POLICY.md)).

## 4. Buyer responsibilities

- Provide accurate delivery and payment information.
- Pay for what you order. Repeated non-payment or chargeback abuse can
  result in account suspension.
- Use the dispute process (in-app: My Orders → Report an issue) for
  problems with an order rather than off-platform harassment of a vendor.
- Reviews must reflect a genuine, completed transaction -- MAUMart only
  allows reviews tied to completed orders for this reason (see
  Section 4.1.6 of the accompanying system design).

## 5. Vendor responsibilities

Covered in full in the [Vendor Agreement](VENDOR_AGREEMENT.md). In
short: list accurately, fulfil what you sell, respond to orders and
disputes in good time, and don't list anything you're not legally
entitled to sell -- Pharmacy & Health listings specifically require
admin approval and are restricted to OTC items (see Section 2.4 of the
system design report).

## 6. Payments

Payments are processed by a third-party payment gateway (Paystack or
Flutterwave in production; a mock gateway in this coursework build).
MAUMart does not store your card details. Funds for a completed order
are released to the vendor per the platform's payout schedule
(`[define once real payouts exist]`); MAUMart may hold funds during an
open dispute.

## 7. Prohibited conduct

No fraud, no listing counterfeit or stolen goods, no circumventing the
platform's payment/review systems, no harassment of other users, no
listing anything illegal to sell in Nigeria (including regulated
medications outside the OTC whitelist -- see Section 2.4).

## 8. Suspension and termination

MAUMart may suspend or terminate an account for violating these Terms,
including confirmed fraud, repeated disputes found in the buyer's or
vendor's fault, or abuse of other users. You can close your own account
at any time (Privacy → Delete my account), which anonymizes your
personal data per the [Privacy Policy](PRIVACY_POLICY.md#6-security-measures-in-place).

## 9. Liability

`[Standard limitation-of-liability language would go here in a real
deployment -- e.g., MAUMart's liability for platform errors is limited
to direct damages up to the value of the affected order; MAUMart is not
liable for a vendor's failure to perform. This needs real legal drafting
before publication -- it is not filled in here because it requires
jurisdiction-specific legal judgment this document doesn't attempt to
supply.]`

## 10. Changes to these Terms

Material changes will be announced in-app before taking effect, mirroring
the Privacy Policy's approach (Section 9 there).

## 11. Governing law

These Terms are governed by the laws of the Federal Republic of Nigeria.
Consumer protection matters are additionally governed by the FCCPA 2018;
data protection matters by the NDPA 2023 (see the Privacy Policy).
