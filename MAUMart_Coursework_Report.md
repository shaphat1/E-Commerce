# MAUMart: A Hybrid Marketplace E-Commerce Application for Modibbo Adama University, Yola

**CSC 720: Electronic Commerce Technologies — Coursework Project Report**
**Modibbo Adama University (MAU), Yola — Faculty of Computing, Department of Computer Science**

---

## Table of Contents
1. Project Overview
2. Feasibility Study
3. Fact-Finding Techniques and Results
4. Software Requirements Specification
5. Algorithms
6. Flowcharts
7. Pseudocode
8. System Design (ERD, Architecture)
9. Source Code
10. Testing Evidence
11. Screenshots & User Documentation
12. Production-Readiness Pass
10. *(next)* Testing Evidence
11. *(next)* Screenshots
12. *(next)* User Documentation

---

## 1. Project Overview

**Working name:** MAUMart

**Concept:** Rather than a single-niche storefront (the assignment's suggested Fashion / Electronics / Groceries / Books / Pharmacy tracks), MAUMart is a **hybrid, multi-vendor marketplace** — closer in structure to Jumia or Konga than to a single shop. Any registered seller (student entrepreneur, campus shop, or approved external vendor) can list under a category; any registered buyer (student, staff, or visitor) can browse across all of them from one app.

**Category taxonomy** (mapped to the assignment's niches, expanded for campus life):
| Category | Examples |
|---|---|
| Books & Study Materials | Textbooks, past questions, lecture note printouts, stationery |
| Electronics & Gadgets | Phones, laptops accessories, power banks, repairs |
| Fashion & Accessories | Clothing, shoes, jewellery, tailoring services |
| Groceries & Provisions | Foodstuff, drinks, hostel provisions |
| Pharmacy & Health | OTC medication, toiletries, first-aid — sold only by verified, licensed vendors (see Legal Feasibility) |
| Food & Snacks | Ready-to-eat food from student/campus vendors |
| Services | Tutoring, printing/photocopying, laundry, hairdressing, phone/laptop repair |
| Hostel & Room Essentials | Mattresses, buckets, reading lamps, extension boxes |

**Actors:**
- **Buyer** — any registered user browsing, searching, and purchasing.
- **Vendor/Seller** — a registered user (or verified business) who lists and manages products.
- **Admin** — MAU-side platform operator: approves vendors, moderates listings, resolves disputes.

**Why "hybrid" is the right call for MAU specifically:** a single-niche app fragments demand across five separate apps that students won't all install; a general campus marketplace concentrates supply and demand the way the lecture notes describe under network effects and community value (Unit 3.2) — each additional vendor and buyer makes the platform more useful to everyone else. It also lets the recommendation/personalization layer (Unit 11) do meaningfully more, since a student's behaviour across categories (bought a textbook, browsed laptop sleeves, searched for jollof rice vendors) is a richer signal than single-category behaviour alone.

---

## 2. Feasibility Study

### 2.1 Technical Feasibility

- **Stack:** Python with **Flet** (built on Flutter). A single Flet codebase compiles to a Windows/Linux/macOS desktop app, a Progressive Web App, and Android/iOS mobile builds — directly satisfying the assignment's "single codebase across Desktop, Web, Mobile" requirement without maintaining parallel Flutter/Dart and Python codebases.
- **Backend:** A lightweight REST API (FastAPI) backed by PostgreSQL, or Firebase/Supabase for a faster MVP path — either is well within the skill set typically available in a Computer Science postgraduate/undergraduate cohort at MAU.
- **Payments:** Integration with a Nigerian payment gateway (Paystack or Flutterwave) gives card, bank transfer, and USSD support out of the box — this maps directly onto Unit 10's point that bank transfer (via NIP) is a first-class Nigerian e-commerce payment method, not an afterthought.
- **Risk:** the team's familiarity with Flet specifically (newer than plain Flutter/React) is the main technical unknown; mitigated by Flet's Python-native API being approachable for a CS cohort already fluent in Python.
- **Verdict: Feasible**, with Flet + FastAPI/Supabase + Paystack/Flutterwave as the recommended stack.

### 2.2 Economic Feasibility

- **Development cost:** primarily developer time (this is a coursework/student project); infrastructure cost is low — Supabase/Firebase free tiers and Paystack's pay-per-transaction pricing mean near-zero fixed cost before revenue.
- **Revenue model options** (Unit 6's knowledge/marketplace commerce models applied to physical goods):
  - **Commission per transaction** (percentage of sale) — the standard marketplace model (Jumia, Etsy).
  - **Vendor subscription tiers** — free basic listing, paid tier for featured placement/analytics.
  - **Promoted listings** — vendors pay for category-top placement, disclosed as "Sponsored" (see Ethical Design Commitments below — this must never be disguised as an organic/personalized recommendation).
- **Benefit case:** reduces reliance on informal WhatsApp-group commerce (searchability, buyer protection, dispute handling), which is the *de facto* current channel for peer-to-peer trade among MAU students.
- **Verdict: Feasible** for a coursework/pilot scope; commission-based revenue is realistic longer-term but not required to justify the coursework build.

### 2.3 Operational Feasibility

- **User acceptance:** MAU's student population already trades informally via WhatsApp/Facebook groups — the behaviour exists, the tool doesn't. Acceptance risk is lower than for a wholly new behaviour.
- **Connectivity constraints:** Adamawa State has patchy and costly mobile data outside campus Wi-Fi zones. Per Unit 9.5's inclusive-design guidance, the app should be **offline-first where possible** (cached catalogue browsing, queued actions that sync on reconnect) and the **PWA build should be lightweight** (Core Web Vitals budget) rather than assuming always-on broadband.
- **Digital literacy:** generally high among the university population, but vendor-side users (e.g. a campus food seller) may need a deliberately simple listing flow — this is a UX requirement, not just a nice-to-have.
- **Verdict: Feasible**, conditional on the low-bandwidth/offline-first design commitments carrying through to implementation, not just being stated here.

### 2.4 Legal Feasibility

- **Data protection:** Nigeria Data Protection Act (NDPA) 2023 governs collection of buyer/vendor personal data (names, phone numbers, addresses, transaction history). MAUMart needs a published privacy notice, a lawful basis for processing, and data-minimisation in what's collected — directly referencing Unit 11.3.1's regulatory-response discussion.
- **Payment compliance:** using a licensed gateway (Paystack/Flutterwave) rather than building custom card handling keeps PCI-DSS scope with the gateway, not the coursework app (Unit 10.2.1).
- **Regulated categories:** Pharmacy/health listings carry real regulatory exposure (NAFDAC rules on sale of medication) — the safe scope for a coursework project is to **restrict Pharmacy to OTC toiletries/first-aid and require vendor verification**, or to build the category as a demonstration only, clearly flagged as not for real medication sales.
- **Institutional permission:** operating commerce "for MAU" implies coordinating with the university's ICT/Student Affairs units if this were to go beyond a coursework prototype — worth a line in the report even though it doesn't block the coursework build itself.
- **Verdict: Feasible for coursework scope**, with the Pharmacy-category caveat above.

### 2.5 Schedule Feasibility

A realistic single-semester coursework schedule (adjust to the actual submission deadline):

| Week(s) | Milestone |
|---|---|
| 1 | Feasibility study, fact-finding, SRS (this phase) |
| 2 | Algorithms, flowcharts, pseudocode, ERD/architecture design |
| 3–5 | Core build: auth, product management, cart, checkout |
| 6 | Order management, vendor dashboard, basic recommendation logic |
| 7 | Testing, bug fixing |
| 8 | Screenshots, user documentation, final report assembly |

**Verdict: Feasible** within a typical 8-week coursework window; tight but workable if scope is held to the MVP defined in the SRS rather than expanding mid-build.

---

## 3. Fact-Finding Techniques and Results

*(Framed as the fact-finding a real requirements-gathering exercise would run — use this as the template to actually go out and collect responses if real interviews/questionnaires are conducted before submission; the findings below are the reasoned baseline for the SRS that follows.)*

**Real instruments now exist.** `elicitation/Elicitation_Instruments.md` (project root) contains the actual interview guides, questionnaire, and observation checklist to run this for real — buyer interviews, vendor interviews, a structured student questionnaire, a WhatsApp/Facebook-group observation checklist, and an institutional stakeholder guide, plus an ethics note on consent and anonymity. The "Expected/likely finding" lines below are what those instruments are designed to test, not a substitute for running them.

### 3.1 Interviews
Target informants: a sample of students (buyers), a few informal campus vendors (e.g. food sellers, phone accessory sellers), and someone from MAU ICT if institutional buy-in is sought.
Key questions: *What do you currently sell/buy on campus and how? What stops you trusting a stranger's listing? What would make you pay online vs. pay-on-delivery?*
**Expected/likely finding:** trust and delivery risk are the dominant concerns (consistent with Unit 2.3's discussion of pay-on-delivery as a market response to perceived financial/delivery risk in Nigerian B2C) — buyer protection features (ratings, verified vendors, in-app dispute reporting) matter more than flashy UI.

### 3.2 Questionnaires
A short structured questionnaire distributed to students/vendors covering: device used most (phone vs. laptop), typical data budget, willingness to pay platform commission (vendors), preferred payment method, categories most wanted.
**Expected/likely finding:** overwhelming mobile-phone usage → mobile/PWA experience is not secondary to desktop, it is primary; bank transfer and USSD likely outrank card payment.

### 3.3 Observation
Observing existing informal channels — MAU-affiliated WhatsApp buy-and-sell groups, Facebook Marketplace posts tagged to Yola — to see what's actually being traded, how listings are described, and how disputes currently get handled (usually informally, by group admins).
**Expected/likely finding:** current "search" is scrolling chat history, which is the single biggest usability gap MAUMart's structured catalogue and search directly solves.

### 3.4 Document Analysis
Review of: the CSC 720 lecture notes and slides themselves (source of the design principles applied throughout this report), the coursework assignment brief, and any existing MAU digital-services documentation (student portal, if applicable) for authentication/identity patterns already familiar to users (e.g. matric number-based login).

### 3.5 Online Research
Benchmarking comparable systems: Jumia/Konga (general marketplace UX patterns), campus-specific marketplace apps at other Nigerian universities where they exist, and Nigerian payment gateway documentation (Paystack/Flutterwave) for integration feasibility.

### 3.6 Synthesis — What the Fact-Finding Drives in the SRS
1. Mobile-first, low-bandwidth-tolerant design is non-negotiable, not a stretch goal.
2. Trust features (vendor verification, ratings/reviews, reporting) are core, not V2.
3. Local payment methods (bank transfer/USSD via NIP-connected gateway) must be first-class alongside card.
4. Search/browse must clearly outperform "scrolling a WhatsApp group" — structured categories, filters, and search are core value, not polish.

---

---

## 4. Software Requirements Specification (SRS)

### 4.1 Functional Requirements

Grouped by module. Each requirement is tagged **FR-x.y** for traceability into the algorithms, flowcharts, and test cases that follow in later sections.

**4.1.1 Authentication & Account Management**
- **FR-1.1** Users register as Buyer or Vendor (a single account can hold both roles); Admin accounts are provisioned separately, not self-registered.
- **FR-1.2** Registration collects name, phone number, email, password, and role; vendors additionally supply a business/stall name and category.
- **FR-1.3** Login supports email/phone + password; passwords are hashed (never stored plain) and a "forgot password" flow resets via OTP/email link.
- **FR-1.4** Vendor accounts require **admin verification** before their listings go live (trust mechanism, Unit 2.3).
- **FR-1.5** Users can view/edit their profile (contact info, delivery address, saved payment preference).

**4.1.2 Product / Listing Management (Vendor-side)**
- **FR-2.1** Vendors create a listing with: title, category, description, price, quantity/stock, photos (1–5), and delivery options (pickup/campus delivery).
- **FR-2.2** Vendors edit or deactivate their own listings; deactivated listings drop out of search/browse but remain in past-order history.
- **FR-2.3** Vendors view a dashboard: active listings, pending orders, sales history, and (if enabled) a "boost this listing" paid-promotion option, clearly labelled **"Sponsored"** wherever it appears in buyer-facing results (Unit 2.7 — dark-pattern avoidance: sponsored placement must never be visually indistinguishable from organic ranking).
- **FR-2.4** Restricted categories (currently: Pharmacy) require an extra vendor-verification step and are limited to a pre-approved product whitelist (OTC/toiletries) rather than free-text listing, per the legal-feasibility scoping in Section 2.4.

**4.1.3 Search, Browse & Discovery (Buyer-side)**
- **FR-3.1** Buyers browse by category, or search by keyword with basic typo-tolerance.
- **FR-3.2** Buyers filter results by price range, category, and vendor rating.
- **FR-3.3** The home feed shows: trending/most-purchased items (rule-based: highest sales in the last 7 days), and a personalized "Recommended for you" rail once the user has enough interaction history (see 4.1.7).
- **FR-3.4** Every recommended or sponsored surface must carry a short, honest explanation ("Because you viewed X" / "Sponsored") — Unit 11.6's transparency principle ("why am I seeing this?") is a functional requirement, not a design nicety.

**4.1.4 Cart & Checkout**
- **FR-4.1** Buyers add items from multiple vendors to a single cart; the cart groups items by vendor for fulfilment purposes even though checkout is one flow.
- **FR-4.2** Checkout shows full landed cost (item price + delivery fee) **before** the final confirm step — no costs revealed only at the last screen (Unit 5.2.4 cart-abandonment causes; also a direct dark-pattern-avoidance commitment from Unit 2.7).
- **FR-4.3** Payment options: card, bank transfer, and USSD via the payment gateway integration (Paystack/Flutterwave); pay-on-delivery may be offered per-vendor as a configurable option, matching current Nigerian buyer trust norms (Unit 2.3).
- **FR-4.4** On successful payment, an order record is created and the vendor is notified.
- **FR-4.5** Guest checkout is **not** offered in v1 (order accountability and dispute handling depend on an authenticated buyer identity) — noted here as a deliberate scope decision, revisit post-MVP.

**4.1.5 Order Management**
- **FR-5.1** Buyers view order status (Placed → Confirmed by vendor → Ready/Out for delivery → Completed) and order history.
- **FR-5.2** Vendors update order status from their dashboard; status changes trigger buyer notifications.
- **FR-5.3** Buyers can cancel an order only while it is still in "Placed" status; cancellation after vendor confirmation requires a dispute/refund request instead.
- **FR-5.4** A lightweight dispute-reporting flow lets a buyer flag an order (not delivered, not as described); flagged orders surface on the Admin dashboard.

**4.1.6 Ratings, Reviews & Trust Signals**
- **FR-6.1** Buyers rate (1–5) and optionally review a vendor after order completion.
- **FR-6.2** Vendor profiles display aggregate rating, number of completed sales, and a "Verified Vendor" badge once admin-approved — implementing the institution-based and vendor-specific trust dimensions from Unit 2.3's trust framework.
- **FR-6.3** Fake-review mitigation: only buyers with a completed order for that vendor can review (verified-purchase reviews, Unit 5.2.1).

**4.1.7 Personalization / Recommendation Engine**
- **FR-7.1** *Cold-start (new user):* show rule-based trending items and category-popular items — no interaction history required (Unit 11.4.5, addresses the CF cold-start problem named in Unit 11.4.4).
- **FR-7.2** *Warm user:* once a buyer has ≥3 recorded interactions (views/purchases), blend in content-based recommendations (similar category/price band to items they engaged with) — Unit 11.4.3.
- **FR-7.3** *Established user base:* item-based collaborative filtering ("customers who bought X also bought Y") once enough platform-wide interaction data exists — Unit 11.4.4, the Amazon-style item-to-item approach, chosen over user-based CF for stability at small-to-medium scale.
- **FR-7.4** Recommendations must be explainable in-UI (see FR-3.4) and must **never** be presented as neutral/organic when a placement is paid — sponsored and personalized are always visually distinguished.
- **FR-7.5** Users can view and clear their "activity used for recommendations" from their profile — a data-minimisation and user-control measure responding to the privacy-personalization paradox (Unit 11.6.2).

**4.1.8 Admin**
- **FR-8.1** Admin approves/rejects vendor verification requests and restricted-category listings.
- **FR-8.2** Admin moderates flagged listings/reviews and resolves disputes escalated from FR-5.4.
- **FR-8.3** Admin views platform-level analytics: GMV, active vendors/buyers, top categories.

### 4.2 Non-Functional Requirements

| Category | Requirement | Rationale (lecture tie-in) |
|---|---|---|
| **Performance** | Product listing pages load in <2s on a 3G-equivalent connection; catalogue images are compressed/responsive | Core Web Vitals as a usability attribute, Unit 9.4.3; Adamawa connectivity constraints, Section 2.3 |
| **Security** | Passwords hashed (bcrypt/argon2); all traffic over TLS; payment data never touches MAUMart's own servers (delegated to gateway) | Unit 10.2.1 — TLS + tokenization + PCI scope reduction via hosted payment pages |
| **Reliability** | Failed payment callbacks are retried with idempotency keys; no double-charging or lost orders on network failure | Unit 8.4.1 — webhook reliability craft; Unit 8.5 — at-least-once delivery, idempotent consumers |
| **Usability** | Core flows (browse → cart → checkout) usable by a first-time vendor with no training; mobile-first responsive layout | Unit 9.1–9.3 — usability as revenue lever, Jakob's Law (use familiar e-commerce conventions) |
| **Scalability** | Architecture supports moving from a single small server to horizontally-scaled hosting without a rewrite (stateless app tier, externalized session/cart state) | Unit 7.3 — horizontal scaling requires statelessness |
| **Maintainability** | Modular codebase (auth, catalogue, cart, orders, recommendations as separate modules); documented API contracts | Unit 7.2 — n-tier separation of concerns |
| **Availability** | Target 99% uptime for a coursework-scale deployment (not 24/7 enterprise SLA, but graceful-degradation principles still apply — e.g. serve cached catalogue if the recommendation service is briefly down) | Unit 7.5.3 — graceful degradation |
| **Privacy/Compliance** | Data collection limited to what's needed for the listed functional requirements; privacy notice published; users can request account/data deletion | NDPA 2023, Unit 11.3.1 |

### 4.3 Constraints & Assumptions
- Coursework timeline (≈8 weeks) caps v1 scope to the requirements above; features explicitly deferred: guest checkout, in-app chat between buyer/vendor, multi-language/vernacular UI, USSD-only access path.
- Assumes access to a Paystack/Flutterwave **test/sandbox** account for coursework development — no real transactions required for grading, only a working sandbox integration.
- Assumes a small seed dataset (demo vendors/products) will be used for testing and screenshots rather than live user-generated content.

---

---

## 5. Algorithms

Step-by-step description of the core-module algorithms named in the assignment deliverables table. Each maps to the FR items above.

### 5.1 Algorithm — User Registration (FR-1.1–1.4)
**Input:** name, phone, email, password, role (Buyer/Vendor), [vendor-only: business name, category]
**Output:** created account record, or validation error

1. Receive registration form input.
2. Validate: email format correct; phone number matches Nigerian format; password meets minimum strength (length ≥ 8, at least one number).
3. Check whether email or phone already exists in the Users table.
   - If yes → return error "Account already exists," offer login/reset instead.
4. Hash the password (bcrypt/argon2) — never store the plain password.
5. Insert new user record with role = Buyer or Vendor, status = "active" (Buyer) or "pending verification" (Vendor).
6. If role = Vendor → create a linked Vendor Profile record (business name, category, verification_status = "pending") and add to Admin's verification queue.
7. Send confirmation (email/SMS).
8. Return success + redirect to login.

### 5.2 Algorithm — Vendor Listing Creation (FR-2.1, FR-2.4)
**Input:** vendor_id, title, category, description, price, quantity, photos[], delivery_options
**Output:** created listing (status: live or pending-review), or validation error

1. Confirm the requesting user is a **verified** vendor (FR-1.4); if not verified → block with message "Complete vendor verification to list products."
2. Validate required fields present; price > 0; quantity ≥ 0.
3. If category is a **restricted category** (currently Pharmacy):
   a. Check product title/description against the pre-approved whitelist.
   b. If not on whitelist → set status = "pending admin review" and stop (do not publish).
4. Upload photos to storage; reject if none provided (minimum 1 required) or if >5 supplied.
5. Insert listing record with status = "live" (or "pending admin review" from step 3).
6. Index the listing for search (title, category, keywords).
7. Return success + listing ID.

### 5.3 Algorithm — Add to Cart and Checkout (FR-4.1–4.4)
**Input:** buyer_id, cart_items[{listing_id, quantity}], delivery_address, payment_method
**Output:** confirmed order(s), or error

1. For each item the buyer adds: check listing is still "live" and quantity requested ≤ available stock; if not, reject that item with a clear message and do not silently drop it.
2. Group cart items by vendor_id (multi-vendor cart, FR-4.1).
3. On "Proceed to Checkout":
   a. Recompute item subtotal + delivery fee per vendor group.
   b. Display full landed cost (FR-4.2) — user must see this screen before confirm is enabled.
4. On "Confirm & Pay":
   a. Create a pending order record per vendor group (so one multi-vendor cart becomes N orders, one per vendor, sharing a parent "checkout session" ID for the buyer's reference).
   b. Call the payment gateway with the total amount and a unique idempotency key = checkout_session_id.
   c. Await gateway callback (webhook).
5. On gateway "success" callback:
   a. Verify the callback signature (per Unit 8.5 message-authenticity practice).
   b. Mark corresponding order(s) as "Confirmed — Paid."
   c. Decrement stock for each purchased listing.
   d. Notify each vendor of their new order.
6. On gateway "failure"/timeout callback → mark order(s) "Payment Failed," release any soft-held stock, notify buyer with retry option.
7. If no callback received within the timeout window → poll gateway status endpoint once before marking as failed (idempotent — never double-charge or double-create the order on retry).

### 5.4 Algorithm — Order Status Update (Vendor Side) (FR-5.1–5.2)
**Input:** vendor_id, order_id, new_status
**Output:** updated order, buyer notification

1. Confirm the order belongs to the requesting vendor.
2. Validate the requested transition is legal given current status:
   `Placed → Confirmed → Ready/Out for Delivery → Completed`
   (no skipping stages backward except via the dispute/cancellation path).
3. If transition invalid → reject with the current allowed next-states.
4. Update order status and timestamp.
5. Push notification to buyer with the new status.
6. If new_status = "Completed" → unlock the review/rating action for the buyer (FR-6.1).

### 5.5 Algorithm — Recommendation Ranking (FR-7.1–7.4)
**Input:** buyer_id (optional — may be an anonymous/new session)
**Output:** ranked list of recommended listings for the home feed

1. If buyer_id is null OR buyer has <3 recorded interactions (views/purchases):
   a. Return **rule-based** results: top-N listings by 7-day sales count within the buyer's likely category (or platform-wide if no signal at all). *(Cold-start path, FR-7.1.)*
2. Else if buyer has ≥3 interactions but platform-wide interaction volume is still low (below the threshold needed for stable collaborative filtering):
   a. Build the buyer's profile vector from categories/price-bands of past views and purchases.
   b. Score candidate listings by similarity (category match + price-band proximity) to that profile.
   c. Return top-N by similarity score. *(Content-based path, FR-7.2.)*
3. Else (enough platform-wide data exists):
   a. Retrieve the buyer's purchase/view history.
   b. For each item in history, look up its pre-computed item-item co-purchase neighbours ("bought X also bought Y").
   c. Aggregate and de-duplicate neighbour candidates across all history items, weighting more recent history items more heavily.
   d. Filter out items the buyer already purchased or that are out of stock.
   e. Return top-N by aggregated score. *(Item-based collaborative filtering path, FR-7.3.)*
4. Regardless of path taken: attach an explanation tag to every result ("Trending," "Because you viewed X," "Customers who bought X also bought this") before returning — recommendations are never returned unlabelled (FR-7.4).
5. If any slot in the returned list is a paid/sponsored placement, mark it "Sponsored" and do **not** let it silently displace an organically-ranked result without the label.

---

---

## 6. Flowcharts

*Figures 1–3 were generated as diagrams during development (registration/login, checkout, order fulfilment). When assembling the final submission, export each as an image and embed it here as Figure 1, Figure 2, and Figure 3 respectively. Standard symbols used throughout: rounded pill = Start/End, rectangle = Process, diamond = Decision.*

**Figure 1 — Registration & Login.** Start → submit registration form → validity/uniqueness check (invalid loops back to a retry, valid proceeds) → create account → branch on role: Vendor accounts land in "pending review" (blocked from listing until admin approval, FR-1.4), Buyer accounts are active immediately → both paths converge at End.

**Figure 2 — Checkout.** Cart ready → review cart grouped by vendor → show full landed cost (items + delivery, always before the confirm step, FR-4.2) → "Confirm & pay?" decision (No returns to cart for edits; Yes proceeds) → call payment gateway with an idempotency key → "Payment success?" decision (No marks the order failed, releases held stock, and notifies the buyer; Yes creates the order, decrements stock, and notifies the vendor) → both paths converge at End.

**Figure 3 — Order Fulfilment.** Order placed (paid) → vendor confirms → vendor marks ready/out for delivery → "Buyer received item?" decision (Yes completes the order and unlocks rating/review, FR-5.1/FR-6.1; No routes to a buyer-raised dispute that lands in the admin queue, FR-5.4, and is resolved or refunded by Admin) → both paths converge at End.

---

---

## 7. Pseudocode

Language-independent pseudocode for the same five core processes described in Section 5, ready to translate directly into Flet/Python and the backend API.

### 7.1 Registration
```
FUNCTION register(name, phone, email, password, role, vendor_info = NULL)
    IF NOT valid_email(email) OR NOT valid_phone(phone) OR NOT strong_password(password) THEN
        RETURN error("Invalid input")
    END IF

    IF user_exists(email) OR user_exists(phone) THEN
        RETURN error("Account already exists")
    END IF

    hashed = hash_password(password)
    user = INSERT INTO Users(name, phone, email, hashed, role, status = "active")

    IF role == "Vendor" THEN
        UPDATE user.status = "pending_verification"
        vendor_profile = INSERT INTO Vendors(user_id = user.id, business_name = vendor_info.business_name,
                                              category = vendor_info.category, verification_status = "pending")
        ADD user TO admin_verification_queue
    END IF

    send_confirmation(user)
    RETURN success(user)
END FUNCTION
```

### 7.2 Vendor listing creation
```
FUNCTION create_listing(vendor_id, title, category, description, price, quantity, photos[], delivery_options)
    vendor = GET Vendors WHERE user_id = vendor_id
    IF vendor.verification_status != "approved" THEN
        RETURN error("Complete vendor verification first")
    END IF

    IF title IS EMPTY OR price <= 0 OR quantity < 0 THEN
        RETURN error("Invalid listing details")
    END IF

    status = "live"
    IF category IN RESTRICTED_CATEGORIES THEN
        IF NOT on_whitelist(category, title) THEN
            status = "pending_admin_review"
        END IF
    END IF

    IF LENGTH(photos) < 1 OR LENGTH(photos) > 5 THEN
        RETURN error("Attach between 1 and 5 photos")
    END IF

    stored_photos = upload(photos)
    listing = INSERT INTO Listings(vendor_id, title, category, description, price,
                                    quantity, stored_photos, delivery_options, status)
    index_for_search(listing)
    RETURN success(listing)
END FUNCTION
```

### 7.3 Add to cart and checkout
```
FUNCTION checkout(buyer_id, cart_items[], delivery_address, payment_method)
    FOR EACH item IN cart_items
        listing = GET Listings WHERE id = item.listing_id
        IF listing.status != "live" OR item.quantity > listing.quantity THEN
            RETURN error("Item unavailable: " + listing.title)
        END IF
    END FOR

    vendor_groups = GROUP cart_items BY vendor_id
    total_landed_cost = 0
    FOR EACH group IN vendor_groups
        group.subtotal = SUM(item.price * item.quantity FOR item IN group.items)
        group.delivery_fee = compute_delivery_fee(group, delivery_address)
        total_landed_cost += group.subtotal + group.delivery_fee
    END FOR

    DISPLAY total_landed_cost TO buyer          // must be shown before confirm is enabled
    WAIT FOR buyer_confirmation

    IF NOT buyer_confirmed THEN
        RETURN cancelled("Returned to cart")
    END IF

    checkout_session_id = generate_id()
    FOR EACH group IN vendor_groups
        order = INSERT INTO Orders(buyer_id, vendor_id = group.vendor_id, items = group.items,
                                    total = group.subtotal + group.delivery_fee,
                                    status = "pending_payment", session_id = checkout_session_id)
    END FOR

    gateway_response = call_payment_gateway(total_landed_cost, payment_method,
                                             idempotency_key = checkout_session_id)

    IF gateway_response == "success" THEN
        FOR EACH order IN orders_for_session(checkout_session_id)
            UPDATE order.status = "confirmed_paid"
            decrement_stock(order.items)
            notify_vendor(order.vendor_id, order)
        END FOR
        RETURN success(orders_for_session(checkout_session_id))
    ELSE
        FOR EACH order IN orders_for_session(checkout_session_id)
            UPDATE order.status = "payment_failed"
            release_held_stock(order.items)
        END FOR
        notify_buyer(buyer_id, "Payment failed, please retry")
        RETURN error("Payment failed")
    END IF
END FUNCTION
```

### 7.4 Order status update (vendor side)
```
FUNCTION update_order_status(vendor_id, order_id, new_status)
    order = GET Orders WHERE id = order_id
    IF order.vendor_id != vendor_id THEN
        RETURN error("Not authorized")
    END IF

    valid_next = ALLOWED_TRANSITIONS[order.status]
    IF new_status NOT IN valid_next THEN
        RETURN error("Invalid transition from " + order.status)
    END IF

    UPDATE order.status = new_status, order.updated_at = NOW()
    notify_buyer(order.buyer_id, order)

    IF new_status == "completed" THEN
        UNLOCK review_action FOR order.buyer_id, order.vendor_id
    END IF

    RETURN success(order)
END FUNCTION
```

### 7.5 Recommendation ranking
```
FUNCTION get_recommendations(buyer_id)
    interactions = COUNT interactions WHERE user_id = buyer_id

    IF buyer_id IS NULL OR interactions < 3 THEN
        RETURN top_n_by_sales(window = "7_days", scope = likely_category(buyer_id) OR "platform_wide")
                 TAGGED "Trending"

    ELSE IF platform_interaction_volume() < CF_MIN_THRESHOLD THEN
        profile_vector = build_profile(buyer_id)     // category + price-band from history
        candidates = ALL live_listings
        scored = FOR EACH c IN candidates: similarity(profile_vector, c)
        RETURN top_n(scored) TAGGED "Because you viewed similar items"

    ELSE
        history = GET recent_history(buyer_id, weighted_by_recency = TRUE)
        neighbours = {}
        FOR EACH item IN history
            item_neighbours = precomputed_item_item_neighbours(item)
            FOR EACH (candidate, score) IN item_neighbours
                neighbours[candidate] += score * item.recency_weight
            END FOR
        END FOR

        REMOVE candidates the buyer already purchased OR out_of_stock
        RETURN top_n(neighbours) TAGGED "Customers who bought this also bought"
    END IF
END FUNCTION

// Every result returned from any branch above carries its explanation tag (FR-7.4).
// Sponsored placements are inserted separately and always tagged "Sponsored" —
// never blended into an organic tag.
```

---

---

## 8. System Design

### 8.1 Entity-Relationship Diagram

*(Rendered as Figure 4 during development. Below is the source — regenerate via mermaid.js `erDiagram` when assembling the final document, or embed the rendered image directly.)*

```
erDiagram
  USERS ||--o| VENDORS : "is"
  VENDORS ||--o{ LISTINGS : lists
  LISTINGS ||--o{ LISTING_PHOTOS : has
  USERS ||--o{ ORDERS : places
  VENDORS ||--o{ ORDERS : fulfills
  ORDERS ||--o{ ORDER_ITEMS : contains
  LISTINGS ||--o{ ORDER_ITEMS : "sold as"
  USERS ||--o{ REVIEWS : writes
  VENDORS ||--o{ REVIEWS : receives
  ORDERS ||--o| REVIEWS : generates
  USERS ||--o{ INTERACTIONS : logs
  LISTINGS ||--o{ INTERACTIONS : "target of"
  ORDERS ||--o| DISPUTES : "may raise"

  USERS { uuid id PK  string name  string email  string phone  string password_hash  string role  string status }
  VENDORS { uuid id PK  uuid user_id FK  string business_name  string category  string verification_status }
  LISTINGS { uuid id PK  uuid vendor_id FK  string title  string category  decimal price  int quantity  string status }
  LISTING_PHOTOS { uuid id PK  uuid listing_id FK  string url }
  ORDERS { uuid id PK  uuid buyer_id FK  uuid vendor_id FK  string session_id  decimal total  string status  timestamp created_at }
  ORDER_ITEMS { uuid id PK  uuid order_id FK  uuid listing_id FK  int quantity  decimal price_at_purchase }
  REVIEWS { uuid id PK  uuid order_id FK  uuid buyer_id FK  uuid vendor_id FK  int rating  string comment }
  INTERACTIONS { uuid id PK  uuid user_id FK  uuid listing_id FK  string type  timestamp created_at }
  DISPUTES { uuid id PK  uuid order_id FK  uuid buyer_id FK  string status  string reason }
```

Design notes: `USERS`–`VENDORS` is optional one-to-one (a user only gets a vendor row when they register to sell). `INTERACTIONS` is deliberately its own append-only table (views, searches, purchases) rather than derived solely from `ORDERS`, because the recommendation engine (Section 5.5 / 7.5) needs view-level signal, not just completed purchases. `REVIEWS` links back to a specific `ORDERS` row (not just a buyer-vendor pair) to enforce the verified-purchase-only review rule, FR-6.3.

### 8.2 System Architecture

*(Rendered as Figure 5 during development — a three-tier architecture.)*

- **Client tier (Flet):** the single Python codebase that compiles to the Desktop, Web, and Mobile builds required by the assignment. Talks to the backend exclusively over HTTPS/REST — no direct database access from the client, keeping the architecture aligned with the client-server and n-tier principles in Unit 7.1–7.2.
- **Application/API tier (FastAPI):** exposes the modules implied by the FRs — Auth, Catalog (listings/search), Cart/Checkout, Orders, and Recommendations — as a stateless service layer, so it can later scale horizontally (Unit 7.3) without a redesign.
- **Data tier:** PostgreSQL for the relational data in the ERD above, plus a Redis cache for session state, hot product/category lookups, and the pre-computed item-item recommendation neighbours (Section 5.5 step 3b) so ranking stays fast without recomputing collaborative-filtering scores per request.
- **Payment gateway (external):** Paystack/Flutterwave handles card, bank transfer, and USSD; MAUMart never stores raw card data, keeping PCI-DSS scope with the gateway (Unit 10.2.1).

---

---

## 9. Source Code

The complete, working codebase is organized as two deployables, matching the client-server architecture in Section 8.2:

```
backend/                  FastAPI + SQLite REST API
  main.py                 App entrypoint, wires up all routers
  models.py                ORM models -- one class per ERD entity (Section 8.1)
  schemas.py               Pydantic request/response contracts
  database.py               SQLite engine/session (swap DATABASE_URL for Postgres in production)
  auth_utils.py             Password hashing (bcrypt) + bearer-token sessions
  payment_gateway.py        Mock Paystack/Flutterwave stand-in, same idempotency-key contract
  seed.py                   Demo data: 6 vendors across categories, 13 listings, 3 buyers, order history
  routers/
    auth.py                 Implements the registration/login algorithm, Section 7.1
    listings.py              Vendor listing creation (Section 7.2), buyer browse/search
    cart.py                   Checkout algorithm, Section 7.3
    orders.py                 Order status transitions (Section 7.4), cancellation, disputes
    reviews.py                 Verified-purchase-only reviews (FR-6.1-6.3)
    recommendations.py         Tiered ranking algorithm, Section 7.5
    interactions.py            View-event logging (recommendation signal)
    admin.py                   Vendor/listing approval, dispute resolution, platform stats
  tests/test_api.py         Formal test-case suite -- see Section 10

frontend/                  Flet client -- one codebase for Desktop, Web, and Mobile
  main.py                  Entrypoint + navigation
  state.py                  Session/cart state
  api_client.py             REST wrapper -- the only module that talks HTTP
  components.py              Shared nav bar, listing card, error banner
  models_client.py           Category list + status flow, mirrored from the backend
  views/                     One module per screen: auth, home, product, cart, orders, vendor, admin
  smoke_test.py               Structural test -- builds every screen against the live backend
```

Every module carries inline comments back to the FR/algorithm/section it implements, so the code and the design docs in Sections 4–7 stay traceable to each other. The full source is in the accompanying `maumart_source_code.zip`; `README.md` at its root covers setup and running both halves.

Two scope decisions worth documenting explicitly:
- **Mock payment gateway.** `payment_gateway.py` stands in for Paystack/Flutterwave with the same idempotency-key contract a real integration needs (Section 7.3 step 4b), so swapping in the real gateway later is a one-file change, not a redesign.
- **SQLite instead of PostgreSQL.** Chosen for zero-setup local development per the coursework schedule (Section 2.5); every query goes through SQLAlchemy's ORM, so moving to Postgres for a real deployment is a one-line `DATABASE_URL` change in `database.py`.

---

## 10. Testing Evidence

Two independent test passes, both runnable from the provided code:

**Backend API test suite (`backend/tests/test_api.py`)** -- 20 test cases against the live API, covering registration/login validation, the vendor-verification gate (FR-1.4), restricted-category review (FR-2.4), checkout with stock validation and overselling protection (Section 7.3), the full order-status state machine including a rejected backwards transition (Section 7.4), verified-purchase-only reviews with the duplicate-review guard (FR-6.3), admin approval flows, and the recommendation endpoint's tagging invariant (FR-7.4). Latest run:

```
ID    Result Description
----------------------------------------------------------------------
TC1   PASS   Register new buyer
TC2   PASS   Duplicate registration is rejected
TC3   PASS   Login with correct credentials
TC4   PASS   Login with wrong password is rejected
TC5   PASS   Weak password rejected at registration
TC6   PASS   Register new vendor -> pending verification
TC7   PASS   Unverified vendor cannot create a listing
TC8   PASS   Admin approves pending vendor
TC9   PASS   Verified vendor creates a live listing
TC10  PASS   Restricted-category listing requires admin review
TC11  PASS   Checkout with valid stock succeeds
TC12  PASS   Stock decrements by purchased quantity
TC13  PASS   Checkout beyond available stock is rejected
TC14  PASS   Backwards order-status transition is rejected
TC15  PASS   Full order-status progression (confirmed -> ready -> completed)
TC16  PASS   Review allowed once order is completed
TC17  PASS   Duplicate review on the same order is rejected
TC18  PASS   Admin approves restricted-category listing
TC19  PASS   Recommendations endpoint returns tagged results
TC20  PASS   Unauthenticated request to a protected endpoint is rejected

20/20 test cases passed
```

Two real bugs were caught and fixed during this testing pass, not just anticipated in the design: a missing `vendor` relationship on the `Order` model that caused 500 errors on every vendor-facing order screen, and a reserved-TLD issue in the seed data's email addresses. Both are the kind of defect that only shows up when the code actually runs, which is the point of doing this pass before writing it up.

**Frontend structural smoke test (`frontend/smoke_test.py`)** -- builds all ten screens (login, register, home as both an anonymous and a logged-in buyer, product detail, cart, order history, vendor dashboard, and admin dashboard, plus a role-gate check) against the live backend:

```
[OK] login_view
[OK] register_view
[OK] home_view (anonymous, trending fallback)
[OK] home_view (buyer, recommendations)
[OK] product_view
[OK] cart_view (with item)
[OK] orders_view
[OK] vendor_view
[OK] vendor accessing admin_view (should redirect, not crash)
[OK] admin_view

10/10 passed
```

This test suite exists because the Flet version in use (0.86.5) has a substantially different control API than older Flet code most references assume (`content=` instead of `text=` on buttons, `ft.Border.all()` instead of `ft.border.all()`, `ft.BoxFit` instead of `ft.ImageFit`) -- the smoke test caught nine such mismatches across the view files in one run, which manual review alone would likely have missed.

**What this doesn't cover:** actual GUI rendering. The development environment this was built in is sandboxed without a display and without network access to Flutter's toolchain, so it can run the Flet web server (confirmed serving HTTP 200 with a valid Flutter web shell) but can't drive a real browser against it to capture the UI itself. Section 11 covers what to do about that.

### 10.1 Security Hardening Pass

The initial build's NFR-Security row (Section 4.2) covered password hashing, TLS-in-transit, and payment-data delegation to the gateway, but left several gaps open by design (flagged as coursework-scope simplifications). A follow-up pass closed the cheap, high-value ones and verified each with a real test rather than just asserting it:

| Gap | Fix | Verified by |
|---|---|---|
| CORS wide open (`allow_origins=["*"]`) | Restricted to an explicit origin list via `MAUMART_ALLOWED_ORIGINS` env var | `curl` preflight from an allowed origin returns `200` + the origin echoed back; a disallowed origin returns `400` with no CORS header |
| No brute-force protection on login/register | In-memory sliding-window rate limiter, 20 attempts / 5 min per IP (`backend/rate_limit.py`) | `backend/tests/test_rate_limit.py`: 20 attempts return `401` (invalid credentials), the 21st–23rd return `429` |
| Session tokens never expired | 24-hour TTL added to the session store; `/auth/logout` invalidates immediately | Direct check that a token with a forced-past `expires_at` is correctly flagged expired |
| No security response headers | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` added via middleware | `curl -i` on any endpoint shows all three headers present |
| Unverified dependency versions | Ran `pip-audit` against both `requirements.txt` files | Clean -- no known vulnerabilities in the pinned versions at time of scan |

The main 20-case regression suite (Section 10 above) was re-run after these changes and still passes 20/20, and the frontend smoke test still passes 10/10 -- the hardening didn't regress existing functionality.

**Deliberately out of scope for this pass:** a real penetration test, HTTPS/TLS itself (expected at a reverse proxy in front of this app in production, not in the app), CSRF tokens (lower risk here since this is a bearer-token API rather than cookie-based session auth), and a tuned Content-Security-Policy header (needs the actual deployed frontend's origin to set correctly, so it's a deployment-time task, not a coursework-demo one).

### 10.2 NDPA 2023 Compliance Pass

Section 2.4 (Legal Feasibility) specified NDPA 2023 obligations at the design stage; FR-7.5 specified a user-facing data control for recommendations. Neither had an actual implementation until this pass. Three data-subject rights are now built, documented in a real privacy policy, and tested rather than just designed:

| NDPA right | Implementation | Verified by |
|---|---|---|
| Access / data portability | `GET /users/me/export` -- full profile, vendor profile, orders, reviews, and recommendation interaction history as one JSON payload | TC21: export returns all expected sections |
| Objection to processing (personalization specifically) | `GET`/`DELETE /interactions/mine` -- view and clear the interaction log that feeds the recommendation engine, without touching order history (FR-7.5) | TC22: an interaction is logged, appears in the list, is cleared, and the list is confirmed empty afterward |
| Erasure | `DELETE /users/me` -- anonymizes name/email/phone, invalidates every active session, makes the old password unusable | TC23: after deletion, the old credentials return 401 on the next login attempt |

**Erasure is implemented as anonymization, not a hard delete** -- orders and reviews are retained with personal identifiers scrubbed, because transaction records have a legitimate retention basis (tax/audit, resolving a dispute on a past order) that NDPA's erasure right doesn't override. `PRIVACY_POLICY.md` (project root) explains this trade-off in plain language, alongside the full policy: what's collected and why, lawful basis per data category, retention periods, third-party sharing (the payment gateway is a separate data controller for card data), and how to exercise each right in-app.

The main regression suite now stands at 23/23 (the three NDPA cases added to the original 20), and the frontend smoke test at 11/11 (adding the new Privacy screen, reachable from the nav bar once logged in).

**Not covered by this pass:** a Data Protection Impact Assessment (DPIA), formal registration with the NDPC, and consent-management UI for cases where consent (rather than contract necessity or legitimate interest) would be the correct lawful basis -- none of MAUMart's current processing needs consent as its basis, but a real deployment handling, say, marketing communications would need to revisit this.

---

## 11. Screenshots & User Documentation

**Screenshots** (assignment deliverable #10) need to be captured on a machine with a display, since they can't be produced in the sandboxed environment this was built in. With the backend running (`uvicorn main:app --reload`) and the frontend running (`flet run main.py --web`), walk through and capture: registration, login, home/browse with the recommendation rail, product detail, cart with the landed-cost breakdown, checkout confirmation, buyer order history (including leaving a review), the vendor dashboard (creating a listing, advancing an order's status), and the admin dashboard (approving a vendor and a restricted-category listing). That sequence covers every FR in Section 4.1 that has a UI surface.

**User documentation** (deliverable #11):
- *Installation:* covered by `README.md` at the project root -- `pip install -r requirements.txt` for each half, `python seed.py`, then `uvicorn main:app --reload` and `flet run main.py`.
- *Buyer guide:* register (or use the seeded buyer login) → browse by category or search → open a product → add to cart → checkout with a delivery address and payment method → track order status and leave a review once completed, or report an issue if something's wrong.
- *Vendor guide:* register as a vendor with a business name and category → wait for admin approval (or use the seeded, pre-approved vendor login) → create listings from the dashboard → monitor incoming orders and advance their status as they're fulfilled.
- *Admin guide:* use the seeded admin login → approve pending vendors and restricted-category listings from the dashboard → resolve open disputes → monitor platform stats (active vendors/buyers, live listings, GMV).
- *FAQ:* "Why can't I list products right after registering as a vendor?" -- accounts start in `pending_verification` until an admin approves them (FR-1.4), which is what stops an unverified seller from publishing. "Why does Pharmacy & Health need extra approval?" -- restricted categories always route to admin review before going live (FR-2.4, Section 2.4).

---

## 12. Production-Readiness Pass

Sections 10.1-10.2 covered security hardening and NDPA compliance. This pass addressed the remainder of a direct gap analysis against what a real 21st-century e-commerce platform needs -- legal documents, tax handling, a real (if untested-live) payment integration, notifications, password recovery, database production-readiness, TLS, structured logging, containerization, CI, and search-engine visibility. As throughout this report, every claim below was checked, not asserted -- and where something genuinely couldn't be verified in this sandboxed environment, that's stated plainly rather than glossed over.

### 12.1 Legal documents and consent

`TERMS_OF_SERVICE.md`, `REFUND_POLICY.md`, and `VENDOR_AGREEMENT.md` (project root) join the existing Privacy Policy -- all four now exist, each with the same "needs real legal review before publication" framing and explicit placeholders for jurisdiction-specific decisions (liability limitation, commission structure) this document deliberately doesn't invent. Registration now requires `agreed_to_terms: true` (schema-validated -- a request without it is rejected with 422, not silently accepted), and the Flet registration screen has an actual checkbox tied to that field, not just a document sitting unreferenced in the repo.

### 12.2 Tax (VAT)

Checkout now calculates Nigeria's standard 7.5% VAT on the items subtotal, stored per-order (`subtotal`, `vat_amount`, `delivery_fee`, `total` are now separate columns, not just a lump total) so the charged rate is preserved historically even if the rate changes later -- the correct approach for anything resembling a tax record. Verified with a dedicated test case computing the expected VAT and total independently and checking the API's response matches to the cent.

### 12.3 Payment gateway: real shape, honestly-scoped verification

`payment_gateway.py` was rebuilt around Paystack's actual API contract (`initialize`/`verify`/`refund` with correct request/response shapes) and `verify_webhook_signature()`, which reimplements Paystack's documented HMAC-SHA512 webhook signing scheme. Five test cases (correct signature accepted, wrong signature/empty signature/tampered body/wrong secret all rejected) all pass -- this is pure computation and needed no network access to verify honestly.

**What wasn't verified, and can't be from here:** `api.paystack.co` is not a network-reachable domain from this development environment, so `PaystackGateway`'s actual HTTP calls have never executed against Paystack's servers. The mock gateway (`MockGateway`) is what actually runs in this build by default, and it's what the main test suite exercises. Before real deployment, someone needs to run a manual test against Paystack's own sandbox/test-mode API from an environment that can reach it -- this report does not claim that's been done.

**Refunds are now real, not just relabeled.** Admin dispute resolution (`POST /admin/disputes/{id}/resolve`) takes a `refund: bool` and, when true, actually calls `payment_gateway.refund()` with the order's stored payment reference and sets the order to a genuine `refunded` status -- verified by a test that raises a dispute, resolves it with a refund, and confirms both the gateway call succeeded and the order status changed correctly.

### 12.4 Notifications

`notifications.py` is a pluggable backend, not a stub: `ConsoleNotificationBackend` (the default, logs instead of delivering) and `SMTPNotificationBackend` (real `smtplib` code). Since no real SMTP relay is reachable from this environment, `SMTPNotificationBackend` was verified against a **local test SMTP server** (`aiosmtpd`) -- a genuine SMTP protocol exchange, checked for correct recipient, subject, and body, just not against a real inbox. This is stated as the honest substitute it is, not represented as equivalent to live delivery. All the order/status/refund/password-reset/email-verification notifications specified back in the original pseudocode (Section 7) are now actually wired to this system -- they weren't before this pass, despite being named in the algorithm descriptions.

### 12.5 Password reset and email verification

Both were specified in the original SRS (FR-1.3's "forgot password" flow) and never built until now. Implemented with hashed, time-limited tokens (15-minute OTP for reset, 24-hour token for verification) -- raw tokens are never stored, only their SHA-256 hash, mirroring the password-hashing discipline elsewhere. Both were tested end-to-end: register → capture the OTP/token from the (console-backend) notification log the same way a real test would read a test inbox → confirm → verify the old password now fails, the new one works, and every prior session was invalidated (password reset) or the account shows `email_verified: true` (verification).

One gap flagged rather than hidden: **nothing currently enforces `email_verified` before checkout or any other action.** The mechanism is real and tested; the policy decision of what to gate behind it wasn't made, because that's a product decision this report shouldn't make unilaterally.

### 12.6 Database: real Postgres, not just a claim

Section 8.2's architecture always specified PostgreSQL for production; the running build was SQLite throughout until this pass. PostgreSQL 16 was actually installed and run in the development environment, `database.py` now reads `DATABASE_URL` from the environment, and the **full 29-case test suite was run against real Postgres and passed**, not just against SQLite. `listings.py`'s search now branches on database dialect: Postgres gets real full-text search (`to_tsvector`/`plainto_tsquery`, ranked by relevance) -- confirmed returning correctly ranked results -- while SQLite keeps the original `ILIKE` behaviour. This is offered as the honest, network-reachable equivalent to the Elasticsearch/OpenSearch named in Section 8.2, since `elastic.co` isn't a reachable domain from this environment either.

**Backup and restore** (`backend/scripts/backup_db.sh`/`restore_db.sh`, using `pg_dump`/`pg_restore`) were not just written but actually exercised: backed up a seeded database (15 users, 15 listings), deliberately destroyed it (`DROP SCHEMA public CASCADE`), restored from the dump, and confirmed every row -- including the admin account by name -- came back correctly.

### 12.7 TLS

A self-signed certificate was generated and uvicorn was actually run over HTTPS on it. Verified: `curl` over HTTPS succeeds, plain HTTP on the same port is refused (proving TLS is actually being enforced, not optional), and the certificate is inspectable via `openssl s_client`. This is a local-development proof that the TLS mechanism works correctly, not a production TLS setup -- a real deployment would terminate TLS at a reverse proxy with a CA-signed certificate, as the architecture in Section 8.2 always assumed.

### 12.8 Structured logging

`main.py` now logs every request as a JSON line (method, path, status, duration, client IP) via a request-logging middleware, plus full tracebacks on unhandled exceptions -- the baseline a real log aggregator (however it's eventually wired up) needs. This replaces silence with something a production incident could actually be debugged from, without claiming an integration with any specific SaaS APM product that isn't network-reachable from this environment.

### 12.9 Docker and CI: correct, but explicitly unverified

`backend/Dockerfile`, `frontend/Dockerfile`, and `docker-compose.yml` exist and are built from the exact commands verified to work directly throughout this report (the same `uvicorn`, `flet run --web`, and `seed.py` invocations). `.github/workflows/ci.yml` runs the real test suites against both SQLite and a Postgres service container, plus the webhook, notification, and accessibility tests.

**Neither has actually been executed.** This development environment has no Docker daemon and no network route to trigger a GitHub Actions run. Both are written correctly against well-documented, standard syntax (Docker's own reference, GitHub's service-container docs) -- but "written correctly against documentation" and "actually run and observed to work" are different claims, and this report has tried throughout to only make the second kind where it's true. Here, it isn't yet. The first real `docker compose up` and the first real push to trigger CI are this configuration's actual first tests.

One real bug this exercise did catch: writing the frontend Dockerfile surfaced that `state.py` hardcoded `http://127.0.0.1:8000` as the API base, which would have silently broken in Docker's networking (where the backend is reachable by service name, not `localhost`). Fixed to read `MAUMART_API_BASE` from the environment -- a small thing, but the kind of bug that specifically shows up when you go through the motions of a real deployment path rather than only running everything on one machine.

### 12.10 SEO: a real server-rendered storefront

Flagged in the earlier gap analysis: Flet renders web output through Flutter's web engine, which draws to canvas rather than semantic HTML -- a search crawler fetching a Flet page sees essentially no content. `backend/routers/storefront.py` adds a genuinely server-rendered public catalog (home, category, product detail, search) using Jinja2 templates, running alongside the existing JSON API on the same FastAPI process. Product pages carry schema.org `Product`/`Offer` JSON-LD structured data (the practical, high-ROI use of the knowledge-representation standards discussed in Unit 6.4 of the lecture notes) and correct Open Graph tags; `robots.txt` and a dynamically generated `sitemap.xml` (covering every category and live listing) complete the basics.

Verified with `curl` -- deliberately, since the whole point is content visible without executing JavaScript: the home page's category links, the product page's structured data, and the sitemap's validity were all checked directly against the raw HTTP response, not through a browser. One real bug caught in the process: the initial sitemap generation didn't XML-escape category names containing `&` (e.g. "Books & Study Materials"), producing invalid XML that would have silently failed in any real search console -- caught by actually parsing the generated sitemap with `xml.etree.ElementTree` rather than eyeballing it, and fixed.

Authenticated actions (login, cart, checkout, all three dashboards) remain in the Flet app, linked from every storefront page -- the same split many real storefronts use between a crawlable public catalog and an app-like authenticated experience.

### 12.11 Accessibility: what was actually checked

Static analysis of the storefront's real rendered HTML (not a claim, not a tool run against a mock) across all four page types: zero images missing `alt` text, no heading-level gaps (no jumping from `<h1>` to `<h3>`), a `lang` attribute present, and every form input correctly labelled. Color contrast was computed mathematically for every text/background pairing in the stylesheet against the WCAG relative-luminance formula -- all five pairings pass AA's 4.5:1 threshold, with ratios between 5.4:1 and 17.4:1.

**What this explicitly is not:** a full WCAG 2.2 AA audit. Real accessibility testing needs a browser and assistive technology (screen readers, keyboard-only navigation) that this sandbox can't run. It also only covers the new SSR storefront -- the Flet-based buyer/vendor/admin dashboards were never accessibility-tested at all, static or otherwise, because Flutter's rendering model doesn't expose the same inspectable HTML this method relies on.

### 12.12 Final regression status

After every change in this pass, the full test suite was re-run: **29/29 backend test cases pass** (the original 20, plus NDPA's 3, plus 6 new cases for consent enforcement, VAT, password reset, and refund execution), confirmed against **both SQLite and real Postgres**. The frontend structural smoke test stands at **11/11**, including the consent checkbox and multi-photo listing fix. Nothing in this pass was left unverified where verification was actually possible in this environment -- and everywhere it wasn't possible, that limit is stated in this section rather than implied away.



### 12.13 Correction: measured performance, concurrency and payment findings

Section 12.12 above states that nothing in the pass "was left unverified where verification was actually possible". That was an overclaim. Concurrency and load were never tested, and a later measurement (single-core sandbox, SQLite, synthetic data, one uvicorn worker) found the following. These findings supersede any statement elsewhere in this report that implies the system is deployment-ready.

| Finding | Measurement |
|---|---|
| Stock overselling | Three simultaneous checkouts for one remaining unit: all three buyers charged (HTTP 200) in each of three trials; final stock -1 or 0 |
| Recommendation endpoint | About 7 s per request at 5,006 orders (5,019 SQL queries, one per order); 0 of 20 requests completed within 60 s at 10 concurrent users |
| Browse endpoint | 500 listings: 507 SQL queries per request, 210 KB unpaginated payload, median 2.4 s and 4 requests/s at 10 concurrent users |
| Live payments | A successful Paystack initialisation returns `pending`; `checkout()` accepts only `success`, so every live payment would be rejected. No webhook route exists, so `verify_webhook_signature()` is tested but unused |

Two statements made earlier are retracted: that SQLite's serialised writes would mask the stock race (it did not; the race reproduces on SQLite), and that going live with the payment gateway requires only setting `MAUMART_PAYMENT_MOCK=false` and supplying a key (it does not; the asynchronous flow is unbuilt). The SSR storefront was unaffected (about 70 requests/s, median 127 ms at 500 listings, since its home page is capped at 12 items).

Not measured: PostgreSQL performance, multi-core or multi-instance behaviour, login throughput under bcrypt cost, and any real network latency. The query counts are engine-independent; the latencies are not.
