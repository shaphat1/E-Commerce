"""
MAUMart -- Flet client entrypoint.

Single codebase, three targets, per the assignment's platform requirement:
    Desktop:  flet run main.py
    Web/PWA:  flet run main.py --web
    Mobile:   flet build apk / flet build ipa   (packaging step; unchanged code)

Run the backend first (see backend/README or the top-level README):
    cd backend && python seed.py && uvicorn main:app --reload
"""
import flet as ft

from state import AppState
from views import auth_view, home_view, product_view, cart_view, orders_view, vendor_view, admin_view, privacy_view


def main(page: ft.Page):
    page.title = "MAUMart"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0

    state = AppState()

    def navigate(route: str, **kwargs):
        page.clean()

        if route == "login":
            view = auth_view.login_view(state, page, navigate)
        elif route == "register":
            view = auth_view.register_view(state, page, navigate)
        elif route == "product":
            view = product_view.build(state, page, navigate, kwargs["listing_id"])
        elif route == "cart":
            view = cart_view.build(state, page, navigate)
        elif route == "orders":
            view = orders_view.build(state, page, navigate)
        elif route == "vendor":
            view = vendor_view.build(state, page, navigate)
        elif route == "admin":
            view = admin_view.build(state, page, navigate)
        elif route == "privacy":
            view = privacy_view.build(state, page, navigate)
        else:  # "home" and any unrecognized route fall back to the browse screen
            view = home_view.build(state, page, navigate)

        page.add(view)
        page.update()

    navigate("home")


if __name__ == "__main__":
    ft.run(main)
