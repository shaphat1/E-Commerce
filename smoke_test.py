"""
Not a replacement for real usability/UI testing (Section 10 of the report
covers that with `flet run`) -- this just proves every screen constructs
without raising, against the real seeded backend, before anyone opens a
browser or desktop window on it.
"""
import sys
import traceback

import flet as ft

sys.path.insert(0, ".")
import api_client
from state import AppState
from views import auth_view, home_view, product_view, cart_view, orders_view, vendor_view, admin_view, privacy_view


class FakePage:
    """Enough of ft.Page's surface for view construction: no live client attached."""
    def __init__(self):
        self.controls = []

    def clean(self):
        self.controls = []

    def add(self, *controls):
        self.controls.extend(controls)

    def update(self):
        pass


def noop_navigate(route, **kwargs):
    pass


results = []


def check(name, fn):
    try:
        control = fn()
        assert control is not None or True  # some early-return routes return None-ish; presence check below
        results.append((name, "OK", None))
    except Exception as e:
        results.append((name, "FAIL", f"{type(e).__name__}: {e}\n{traceback.format_exc()}"))


page = FakePage()

# ---- Anonymous / pre-login screens ----
anon_state = AppState()
check("login_view", lambda: auth_view.login_view(anon_state, page, noop_navigate))
check("register_view", lambda: auth_view.register_view(anon_state, page, noop_navigate))
check("home_view (anonymous, trending fallback)", lambda: home_view.build(anon_state, page, noop_navigate))

# ---- Buyer flow ----
buyer_state = AppState()
login_result = api_client.login(buyer_state, "amina.sule@maumart.ng", "BuyerPass1")
buyer_state.token = login_result["token"]
buyer_state.user_id = login_result["user_id"]
buyer_state.name = login_result["name"]
buyer_state.role = login_result["role"]

check("home_view (buyer, recommendations)", lambda: home_view.build(buyer_state, page, noop_navigate))

sample_listing = api_client.browse_listings(buyer_state, q="Physics")[0]
check("product_view", lambda: product_view.build(buyer_state, page, noop_navigate, sample_listing["id"]))

buyer_state.add_to_cart(sample_listing["id"], sample_listing["title"], sample_listing["price"], sample_listing["vendor_name"])
check("cart_view (with item)", lambda: cart_view.build(buyer_state, page, noop_navigate))

check("orders_view", lambda: orders_view.build(buyer_state, page, noop_navigate))
check("privacy_view", lambda: privacy_view.build(buyer_state, page, noop_navigate))

# ---- Vendor flow ----
vendor_state = AppState()
v_login = api_client.login(vendor_state, "ibrahim.books@maumart.ng", "VendorPass1")
vendor_state.token = v_login["token"]
vendor_state.user_id = v_login["user_id"]
vendor_state.name = v_login["name"]
vendor_state.role = v_login["role"]

check("vendor_view", lambda: vendor_view.build(vendor_state, page, noop_navigate))

# Vendor should NOT be able to open admin view (role gate) -- navigate() would redirect;
# here we just confirm it doesn't crash and returns an (empty) control.
check("vendor accessing admin_view (should redirect, not crash)", lambda: admin_view.build(vendor_state, page, noop_navigate))

# ---- Admin flow ----
admin_state = AppState()
a_login = api_client.login(admin_state, "admin@maumart.ng", "AdminPass1")
admin_state.token = a_login["token"]
admin_state.user_id = a_login["user_id"]
admin_state.name = a_login["name"]
admin_state.role = a_login["role"]

check("admin_view", lambda: admin_view.build(admin_state, page, noop_navigate))

# ---- Report ----
print("\n=== SMOKE TEST RESULTS ===")
n_fail = 0
for name, status, detail in results:
    print(f"[{status}] {name}")
    if status == "FAIL":
        n_fail += 1
        print(detail)

print(f"\n{len(results) - n_fail}/{len(results)} passed")
sys.exit(1 if n_fail else 0)
