import flet as ft

import api_client
from components import nav_bar, error_banner

DELIVERY_FEE_PER_VENDOR = 500.0  # mirrors backend/routers/cart.py DELIVERY_FEE_FLAT
VAT_RATE = 0.075                 # mirrors backend models.VAT_RATE; the server's figure is authoritative


def build(state, page, navigate):
    if not state.logged_in:
        navigate("login")
        return ft.Column([])

    address_field = ft.TextField(label="Delivery address", width=400, value="MAU Hostel, Yola")
    payment_dropdown = ft.Dropdown(
        label="Payment method", width=400, value="card",
        options=[
            ft.dropdown.Option("card", "Card"),
            ft.dropdown.Option("bank_transfer", "Bank transfer"),
            ft.dropdown.Option("ussd", "USSD"),
            ft.dropdown.Option("pay_on_delivery", "Pay on delivery"),
        ],
    )
    status_box = ft.Column([])

    def vendor_groups():
        groups = {}
        for line in state.cart:
            groups.setdefault(line.vendor_name, []).append(line)
        return groups

    def render_cart():
        lines_ui = []
        for line in state.cart:
            def make_remove(listing_id):
                def handler(e):
                    state.remove_from_cart(listing_id)
                    refresh()
                return handler

            lines_ui.append(ft.Row([
                ft.Text(f"{line.title} x{line.quantity}", expand=True),
                ft.Text(f"₦{line.price * line.quantity:,.0f}"),
                ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, on_click=make_remove(line.listing_id)),
            ]))

        groups = vendor_groups()
        subtotal = state.cart_total()
        delivery_total = DELIVERY_FEE_PER_VENDOR * len(groups)
        vat_total = round(sum(
            round(sum(l.price * l.quantity for l in lines) * VAT_RATE, 2) for lines in groups.values()), 2)
        landed_total = subtotal + vat_total + delivery_total

        cost_breakdown = ft.Column([
            ft.Divider(),
            ft.Row([ft.Text("Items subtotal"), ft.Text(f"₦{subtotal:,.0f}")], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([ft.Text("VAT (7.5%)"), ft.Text(f"₦{vat_total:,.0f}")], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([ft.Text(f"Delivery ({len(groups)} vendor(s) x ₦{DELIVERY_FEE_PER_VENDOR:,.0f})"),
                    ft.Text(f"₦{delivery_total:,.0f}")], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([ft.Text("Total (full landed cost)", weight=ft.FontWeight.BOLD),
                    ft.Text(f"₦{landed_total:,.0f}", weight=ft.FontWeight.BOLD)],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ]) if state.cart else ft.Container(height=0)

        return lines_ui, cost_breakdown

    def do_checkout(e):
        if not state.cart:
            return
        items = [{"listing_id": l.listing_id, "quantity": l.quantity} for l in state.cart]
        try:
            orders = api_client.checkout(state, items, address_field.value, payment_dropdown.value)
        except api_client.ApiError as err:
            status_box.controls = [error_banner(f"Payment failed: {err}")]
            page.update()
            return
        state.cart = []
        pending = [o for o in orders if o["status"] == "pending_payment" and o.get("payment_url")]
        lines = [f"- {o['vendor_name']}: ₦{o['total']:,.0f} ({o['status'].replace('_', ' ')})" for o in orders]
        if pending:
            # Live gateway: the buyer must finish paying on the provider's hosted page.
            ref = pending[0]["payment_reference"]
            verify_msg = ft.Text("")

            def check_payment(e):
                try:
                    updated = api_client.verify_payment(state, ref)
                except api_client.ApiError as err:
                    verify_msg.value, verify_msg.color = str(err), ft.Colors.RED
                else:
                    if all(o["status"] != "pending_payment" for o in updated):
                        verify_msg.value, verify_msg.color = "Payment confirmed -- thank you!", ft.Colors.GREEN_800
                    else:
                        verify_msg.value, verify_msg.color = "Not paid yet. Finish paying, then check again.", ft.Colors.ORANGE_800
                page.update()

            status_box.controls = [
                ft.Text("Almost done: complete your payment", weight=ft.FontWeight.BOLD),
                ft.Text("Your items are reserved while you pay. Unpaid reservations are released automatically."),
            ] + [ft.Text(t) for t in lines] + [
                ft.ElevatedButton(content="Pay now", url=pending[0]["payment_url"]),
                ft.OutlinedButton(content="I've paid -- check status", on_click=check_payment),
                verify_msg,
                ft.TextButton(content="View my orders", on_click=lambda e: navigate("orders")),
            ]
        else:
            status_box.controls = [
                ft.Text("Order placed successfully!", color=ft.Colors.GREEN_800, weight=ft.FontWeight.BOLD),
                ft.Text(f"{len(orders)} order(s) created. Total charged shown per vendor below."),
            ] + [ft.Text(t) for t in lines] + [
                ft.ElevatedButton(content="View my orders", on_click=lambda e: navigate("orders")),
            ]
        page.update()

    root = ft.Column([], spacing=16)

    def refresh():
        lines_ui, cost_breakdown = render_cart()
        root.controls = [
            nav_bar(state, navigate, "cart"),
            ft.Container(
                content=ft.Column([
                    ft.Text("Your cart", size=22, weight=ft.FontWeight.BOLD),
                    ft.Column(lines_ui) if lines_ui else ft.Text("Your cart is empty.", italic=True),
                    cost_breakdown,
                    ft.Divider(),
                    address_field,
                    payment_dropdown,
                    ft.ElevatedButton(content="Confirm & pay", on_click=do_checkout, disabled=not state.cart),
                    status_box,
                ], spacing=12),
                padding=24, width=460,
            ),
        ]
        page.update()

    refresh()
    return root
