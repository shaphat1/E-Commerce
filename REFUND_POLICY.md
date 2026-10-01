# MAUMart Refund & Return Policy

*Coursework deliverable. Not a substitute for legal review. Placeholders marked `[...]`.*

## 1. What this covers

This policy governs disputed orders raised through **My Orders → Report
an issue** (implements FR-5.4 in the system design report) and how
MAUMart's admin team resolves them (FR-8.2).

## 2. Grounds for a refund

A buyer may request a refund if:
- the item never arrived within the vendor's stated delivery window,
- the item received is materially different from the listing (wrong
  item, significantly not as described, defective on arrival), or
- the order was charged but never confirmed by the vendor.

MAUMart does not mediate change-of-mind returns unless the individual
vendor's own listing states otherwise -- check the listing description
before ordering. This mirrors standard marketplace practice: the vendor,
not MAUMart, sets return terms beyond the baseline protections here,
consistent with the vendor being the seller of record (Terms of
Service, Section 3).

## 3. How a dispute is resolved

1. Buyer files a dispute on the order (reason required).
2. It appears in the admin dispute queue (`GET /admin/disputes`).
3. Admin reviews -- typically by checking order status history and, where
   needed, contacting the buyer and/or vendor for more information
   (this coursework build doesn't yet include in-app messaging for that
   step; see the system design report's list of deferred features).
4. Admin resolves the dispute with one of two outcomes:
   - **Resolved, no refund** -- the order stands (e.g. delivery
     confirmed after the report was filed, or the dispute doesn't meet
     the grounds in Section 2).
   - **Refunded** -- the order's payment is reversed through the payment
     gateway, and the order is marked `refunded`.
5. Both outcomes notify the buyer (and vendor, where relevant) once the
   platform's notification system is configured with real delivery
   (see the system design report's notification-system section).

## 4. Refund timing and method

Refunds are issued back to the original payment method through the
payment gateway. Processing time depends on the gateway and the
buyer's bank -- typically 3-7 business days in production use with
Paystack/Flutterwave; this coursework build's mock gateway processes
refunds instantly since there's no real bank in the loop.

## 5. Vendor's stake in a refund

A refund reverses the vendor's payout for that order. Vendors can see
the outcome of a dispute against their orders in their dashboard.
Repeated refunds against a vendor, especially for "materially different
from listing," may affect their standing on the platform (see Vendor
Agreement).

## 6. What this policy doesn't cover

- Disputes between two users outside of a completed order (e.g. a
  message exchange gone wrong) -- MAUMart's dispute process is
  order-scoped.
- Regulatory returns for restricted-category items (Pharmacy & Health)
  -- these follow whatever NAFDAC/consumer-health rules apply, which
  this coursework build doesn't attempt to encode; a real deployment
  selling in that category would need pharmacy-specific compliance
  review, not just this generic policy.
