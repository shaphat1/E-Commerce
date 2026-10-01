# MAUMart Vendor Agreement

*Coursework deliverable. Not a substitute for legal review. Placeholders marked `[...]`.*

This agreement applies in addition to the general [Terms of
Service](TERMS_OF_SERVICE.md) once your vendor account is approved
(implements FR-1.4's verification gate).

## 1. Becoming a verified vendor

Registering as a vendor creates an account in `pending_verification`
status. You cannot list products until an admin approves your account
(`POST /admin/vendors/{id}/approve` in the system design). Approval is
at MAUMart's discretion and may consider your stated business name and
category.

## 2. What you can list

- List accurately: title, price, quantity, and description must reflect
  the real item. Photos should be of the actual item where practical.
- **Restricted categories** (currently Pharmacy & Health) require an
  extra admin review per listing and are limited to OTC items only --
  see Section 2.4 of the system design report for why. Attempting to
  list a prescription-only or otherwise regulated item outside this
  scope is a violation of this agreement, independent of any external
  regulatory consequence.
- Don't list counterfeit, stolen, or illegal goods.

## 3. Fulfilling orders

- Confirm or reject an incoming order promptly. An unconfirmed order
  sitting indefinitely harms buyer trust in the whole platform, not
  just your storefront.
- Keep your listed quantity accurate -- the platform blocks checkout
  once stock hits zero (Section 5.3/7.3), but only if your count is
  correct.
- Update order status as you fulfil it (confirmed → ready/out for
  delivery → completed) so buyers can see progress and become eligible
  to review the order (Section 4.1.6).

## 4. Fees

`[MAUMart's commission structure would go here -- e.g. a percentage per
completed sale, per Section 2.2's revenue-model options in the system
design report. Left as a placeholder because it's a business decision,
not something this document should invent on your behalf.]`

## 5. Reviews and reputation

Buyers can only review a vendor after a completed order they actually
placed (FR-6.3) -- you cannot solicit fake reviews, and doing so is
grounds for suspension. Your aggregate rating and completed-sales count
are shown publicly on your storefront (FR-6.2) as the platform's main
trust signal for new buyers.

## 6. Disputes

If a buyer disputes an order against you, you may be contacted for more
information before it's resolved (see [Refund & Return Policy](REFUND_POLICY.md)).
A pattern of disputes resolved against you may affect your standing,
including possible suspension of your ability to list new products.

## 7. Termination

MAUMart may suspend a vendor account for violating this agreement or
the general Terms of Service. You may deactivate your own listings or
close your account at any time; closing your account deactivates all
your active listings (Privacy → Delete my account anonymizes your
vendor profile and deactivates your listings, per the system design
report's account-deletion behaviour).

## 8. Taxes

You are responsible for your own tax obligations on income earned
through MAUMart, independent of any VAT MAUMart may collect and remit
on the platform fee itself. `[A real deployment would state clearly
whether MAUMart issues any tax documentation to vendors -- left
unresolved here as a business/legal decision, not a technical one.]`
