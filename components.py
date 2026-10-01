import flet as ft

import api_client


def nav_bar(state, navigate, active: str = ""):
    """Top navigation row -- links shown depend on login state and role."""

    def link(label, route, key):
        return ft.TextButton(
            content=label,
            on_click=lambda e: navigate(route),
            style=ft.ButtonStyle(color=ft.Colors.BLUE_700 if key == active else None),
        )

    items = [
        ft.Text("MAUMart", weight=ft.FontWeight.BOLD, size=20, color=ft.Colors.BLUE_900),
        link("Home", "home", "home"),
    ]

    if state.logged_in:
        cart_count = sum(l.quantity for l in state.cart)
        items.append(link(f"Cart ({cart_count})", "cart", "cart"))
        items.append(link("My orders", "orders", "orders"))
        if state.role == "vendor":
            items.append(link("Vendor dashboard", "vendor", "vendor"))
        if state.role == "admin":
            items.append(link("Admin", "admin", "admin"))
        items.append(link("Privacy", "privacy", "privacy"))
        items.append(ft.Text(f"  Hi, {state.name}", italic=True))
        def do_logout(e):
            api_client.logout(state)
            state.logout()
            navigate("home")

        items.append(ft.TextButton(content="Logout", on_click=do_logout))
    else:
        items.append(link("Login", "login", "login"))
        items.append(link("Register", "register", "register"))

    return ft.Container(
        content=ft.Row(items, alignment=ft.MainAxisAlignment.START, spacing=16),
        padding=ft.Padding(16, 12, 16, 12),
        bgcolor=ft.Colors.SURFACE,
        border=ft.Border.only(bottom=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT)),
    )


def error_banner(message: str):
    if not message:
        return ft.Container(height=0)
    return ft.Container(
        content=ft.Text(message, color=ft.Colors.ON_ERROR_CONTAINER),
        bgcolor=ft.Colors.ERROR_CONTAINER,
        padding=12,
        border_radius=8,
        margin=ft.Margin(0, 8, 0, 8),
    )


def listing_card(listing: dict, navigate):
    photo = listing.get("photo_urls") or []
    reason = listing.get("reason")
    return ft.Container(
        content=ft.Column([
            ft.Container(
                content=ft.Image(src=photo[0], fit=ft.BoxFit.COVER, error_content=ft.Icon(ft.Icons.IMAGE_NOT_SUPPORTED))
                if photo else ft.Icon(ft.Icons.SHOPPING_BAG, size=48),
                height=120, alignment=ft.Alignment.CENTER,
            ),
            ft.Text(listing["title"], weight=ft.FontWeight.BOLD, max_lines=2),
            ft.Text(listing["vendor_name"], size=12, color=ft.Colors.OUTLINE),
            ft.Text(f"₦{listing['price']:,.0f}", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_800),
            ft.Text(reason, size=11, italic=True, color=ft.Colors.BLUE_700) if reason else ft.Container(height=0),
            ft.ElevatedButton(content="View", on_click=lambda e: navigate("product", listing_id=listing["id"])),
        ], spacing=4),
        width=220, padding=12, border_radius=12, bgcolor=ft.Colors.SURFACE,
        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
    )
