"""
Thin wrapper over `requests` for every backend endpoint the client needs.
Keeping all HTTP calls in one module means the views never touch `requests`
directly, and swapping the transport later (e.g. adding retries) is one file.
"""
import requests

TIMEOUT = 20  # seconds; without one a stalled backend hangs the UI forever


class ApiError(Exception):
    pass


def _call(method, url, **kwargs):
    """Every HTTP call goes through here so network failures surface as ApiError, not a crash."""
    kwargs.setdefault("timeout", TIMEOUT)
    try:
        return requests.request(method, url, **kwargs)
    except requests.RequestException:
        raise ApiError("Cannot reach the MAUMart server. Check your connection and try again.")


def _headers(state):
    h = {"Content-Type": "application/json"}
    if state.token:
        h["Authorization"] = f"Bearer {state.token}"
    return h


def _handle(resp):
    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        raise ApiError(str(detail))
    if resp.text:
        return resp.json()
    return None


# ---------- Auth ----------

def register(state, name, email, phone, password, role, business_name=None, vendor_category=None, agreed_to_terms=False):
    payload = {
        "name": name, "email": email, "phone": phone, "password": password,
        "role": role, "agreed_to_terms": agreed_to_terms,
    }
    if business_name:
        payload["business_name"] = business_name
    if vendor_category:
        payload["vendor_category"] = vendor_category
    resp = _call("POST", f"{state.api_base}/auth/register", json=payload)
    return _handle(resp)


def login(state, email, password):
    resp = _call("POST", f"{state.api_base}/auth/login", json={"email": email, "password": password})
    return _handle(resp)


def logout(state):
    if not state.token:
        return
    try:
        _call("POST", f"{state.api_base}/auth/logout", headers=_headers(state))
    except ApiError:
        pass  # logging out locally must work even if the server is unreachable


# ---------- Listings ----------

def get_categories(state):
    resp = _call("GET", f"{state.api_base}/listings/categories")
    return _handle(resp)


def browse_listings(state, category=None, q=None, min_price=None, max_price=None, limit=50, offset=0):
    params = {k: v for k, v in {
        "category": category, "q": q, "min_price": min_price, "max_price": max_price,
        "limit": limit, "offset": offset,
    }.items() if v not in (None, "")}
    resp = _call("GET", f"{state.api_base}/listings", params=params)
    return _handle(resp)


def get_listing(state, listing_id):
    resp = _call("GET", f"{state.api_base}/listings/{listing_id}")
    return _handle(resp)


def create_listing(state, title, category, description, price, quantity, photo_urls, delivery_options="pickup"):
    payload = {
        "title": title, "category": category, "description": description,
        "price": price, "quantity": quantity, "photo_urls": photo_urls,
        "delivery_options": delivery_options,
    }
    resp = _call("POST", f"{state.api_base}/listings", json=payload, headers=_headers(state))
    return _handle(resp)


def my_listings(state):
    resp = _call("GET", f"{state.api_base}/listings/vendor/mine", headers=_headers(state))
    return _handle(resp)


# ---------- Interactions / recommendations ----------

def log_view(state, listing_id):
    if not state.token:
        return
    try:
        _call("POST", f"{state.api_base}/interactions/view/{listing_id}", headers=_headers(state))
    except ApiError:
        pass  # a failed analytics ping must never break the product page


def get_recommendations(state):
    resp = _call("GET", f"{state.api_base}/recommendations", headers=_headers(state))
    return _handle(resp)


def get_my_interactions(state):
    resp = _call("GET", f"{state.api_base}/interactions/mine", headers=_headers(state))
    return _handle(resp)


def clear_my_interactions(state):
    resp = _call("DELETE", f"{state.api_base}/interactions/mine", headers=_headers(state))
    return _handle(resp)


def export_my_data(state):
    resp = _call("GET", f"{state.api_base}/users/me/export", headers=_headers(state))
    return _handle(resp)


def delete_my_account(state):
    resp = _call("DELETE", f"{state.api_base}/users/me", headers=_headers(state))
    return _handle(resp)


def get_trending(state, category=None):
    params = {"category": category} if category else {}
    resp = _call("GET", f"{state.api_base}/recommendations/trending", params=params)
    return _handle(resp)


# ---------- Cart / checkout ----------

def checkout(state, items, delivery_address, payment_method):
    payload = {"items": items, "delivery_address": delivery_address, "payment_method": payment_method}
    resp = _call("POST", f"{state.api_base}/cart/checkout", json=payload, headers=_headers(state))
    return _handle(resp)


def verify_payment(state, reference):
    """Ask the backend to confirm a pending payment with the gateway ("I've paid")."""
    resp = _call("POST", f"{state.api_base}/payments/verify/{reference}", headers=_headers(state))
    return _handle(resp)


# ---------- Orders ----------

def cancel_order(state, order_id):
    resp = _call("POST", f"{state.api_base}/orders/{order_id}/cancel", headers=_headers(state))
    return _handle(resp)


def my_orders(state):
    resp = _call("GET", f"{state.api_base}/orders/mine", headers=_headers(state))
    return _handle(resp)


def incoming_orders(state):
    resp = _call("GET", f"{state.api_base}/orders/vendor/incoming", headers=_headers(state))
    return _handle(resp)


def update_order_status(state, order_id, new_status):
    resp = _call("PATCH", f"{state.api_base}/orders/{order_id}/status",
                           json={"new_status": new_status}, headers=_headers(state))
    return _handle(resp)


def raise_dispute(state, order_id, reason):
    resp = _call("POST", f"{state.api_base}/orders/disputes",
                          json={"order_id": order_id, "reason": reason}, headers=_headers(state))
    return _handle(resp)


# ---------- Reviews ----------

def create_review(state, order_id, rating, comment):
    resp = _call("POST", f"{state.api_base}/reviews",
                          json={"order_id": order_id, "rating": rating, "comment": comment},
                          headers=_headers(state))
    return _handle(resp)


def vendor_reviews(state, vendor_id):
    resp = _call("GET", f"{state.api_base}/reviews/vendor/{vendor_id}")
    return _handle(resp)


# ---------- Admin ----------

def pending_vendors(state):
    resp = _call("GET", f"{state.api_base}/admin/vendors/pending", headers=_headers(state))
    return _handle(resp)


def approve_vendor(state, vendor_id):
    resp = _call("POST", f"{state.api_base}/admin/vendors/{vendor_id}/approve", headers=_headers(state))
    return _handle(resp)


def pending_listings(state):
    resp = _call("GET", f"{state.api_base}/admin/listings/pending", headers=_headers(state))
    return _handle(resp)


def approve_listing(state, listing_id):
    resp = _call("POST", f"{state.api_base}/admin/listings/{listing_id}/approve", headers=_headers(state))
    return _handle(resp)


def open_disputes(state):
    resp = _call("GET", f"{state.api_base}/admin/disputes", headers=_headers(state))
    return _handle(resp)


def resolve_dispute(state, dispute_id, refund):
    resp = _call("POST", f"{state.api_base}/admin/disputes/{dispute_id}/resolve",
                 json={"refund": bool(refund)}, headers=_headers(state))
    return _handle(resp)


def platform_stats(state):
    resp = _call("GET", f"{state.api_base}/admin/stats", headers=_headers(state))
    return _handle(resp)
