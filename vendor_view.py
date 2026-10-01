import flet as ft

import api_client
import models_client  # category list + status flow, mirrored from the backend
from components import nav_bar, error_banner


def build(state, page, navigate):
    if not state.logged_in or state.role != "vendor":
        navigate("home")
        return ft.Column([])

    # ---------- Create listing form ----------
    title_field = ft.TextField(label="Title", width=340)
    category_field = ft.Dropdown(
        label="Category", width=340,
        options=[ft.dropdown.Option(c) for c in models_client.CATEGORIES],
    )
    description_field = ft.TextField(label="Description", width=340, multiline=True, min_lines=2)
    price_field = ft.TextField(label="Price (₦)", width=160)
    quantity_field = ft.TextField(label="Quantity", width=160)
    photo_fields = [ft.TextField(label="Photo URL 1", width=340, hint_text="https://...")]
    photo_fields_column = ft.Column(photo_fields)
    create_status = ft.Text("")

    def add_photo_field(e):
        if len(photo_fields) >= 5:
            return
        photo_fields.append(ft.TextField(label=f"Photo URL {len(photo_fields) + 1}", width=340, hint_text="https://..."))
        photo_fields_column.controls = list(photo_fields)
        page.update()

    listings_column = ft.Column([], spacing=10)
    orders_column = ft.Column([], spacing=10)

    def load_listings():
        listings_column.controls.clear()
        try:
            listings = api_client.my_listings(state)
        except api_client.ApiError as err:
            listings_column.controls.append(error_banner(str(err)))
            page.update()
            return
        if not listings:
            listings_column.controls.append(ft.Text("You have no listings yet.", italic=True))
        for l in listings:
            listings_column.controls.append(ft.Row([
                ft.Text(l["title"], expand=True),
                ft.Text(f"₦{l['price']:,.0f}"),
                ft.Text(f"{l['quantity']} in stock", size=12, color=ft.Colors.OUTLINE),
                ft.Container(
                    content=ft.Text(l["status"], size=11),
                    bgcolor=ft.Colors.AMBER_100 if l["status"] == "pending_admin_review" else ft.Colors.GREEN_100,
                    padding=6, border_radius=6,
                ),
            ]))
        page.update()

    def create_listing(e):
        try:
            price = float(price_field.value)
            quantity = int(quantity_field.value)
        except (ValueError, TypeError):
            create_status.value = "Enter a valid price and quantity."
            create_status.color = ft.Colors.RED
            page.update()
            return
        photo_urls = [f.value.strip() for f in photo_fields if f.value and f.value.strip()]
        if not (title_field.value and category_field.value and photo_urls):
            create_status.value = "Title, category, and at least one photo URL are required."
            create_status.color = ft.Colors.RED
            page.update()
            return
        try:
            listing = api_client.create_listing(
                state, title_field.value.strip(), category_field.value,
                description_field.value.strip(), price, quantity, photo_urls,
            )
        except api_client.ApiError as err:
            create_status.value = str(err)
            create_status.color = ft.Colors.RED
            page.update()
            return
        note = " (pending admin review -- restricted category)" if listing["status"] == "pending_admin_review" else ""
        create_status.value = f"Listing created{note}."
        create_status.color = ft.Colors.GREEN_800
        title_field.value = ""
        description_field.value = ""
        price_field.value = ""
        quantity_field.value = ""
        photo_fields.clear()
        photo_fields.append(ft.TextField(label="Photo URL 1", width=340, hint_text="https://..."))
        photo_fields_column.controls = list(photo_fields)
        page.update()
        load_listings()

    # ---------- Incoming orders ----------
    def load_orders(e=None):
        orders_column.controls.clear()
        try:
            orders = api_client.incoming_orders(state)
        except api_client.ApiError as err:
            orders_column.controls.append(error_banner(str(err)))
            page.update()
            return
        if not orders:
            orders_column.controls.append(ft.Text("No orders yet.", italic=True))
        for o in orders:
            orders_column.controls.append(order_row(o))
        page.update()

    def order_row(o):
        allowed_next = models_client.ORDER_STATUS_FLOW.get(o["status"], [])
        # Vendor only ever advances an order forward, never touches pending_payment/payment_failed.
        vendor_actionable = [s for s in allowed_next if s not in ("payment_failed",)]

        status_msg = ft.Text("")

        def make_advance(order_id, new_status):
            def handler(e):
                try:
                    api_client.update_order_status(state, order_id, new_status)
                except api_client.ApiError as err:
                    status_msg.value = str(err)
                    status_msg.color = ft.Colors.RED
                    page.update()
                else:
                    load_orders()
            return handler

        buttons = [
            ft.ElevatedButton(content=f"Mark {s.replace('_', ' ')}", on_click=make_advance(o["id"], s))
            for s in vendor_actionable
        ]

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(f"Order for ₦{o['total']:,.0f}", weight=ft.FontWeight.BOLD, expand=True),
                    ft.Text(o["status"], size=12, color=ft.Colors.BLUE_700),
                ]),
                ft.Text(f"Deliver to: {o['delivery_address']}", size=12, color=ft.Colors.OUTLINE),
                ft.Row(buttons, spacing=8) if buttons else ft.Text("No further action needed.", size=12, italic=True),
                status_msg,
            ], spacing=6),
            padding=14, border_radius=10, border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT), width=460,
        )

    load_listings()
    load_orders()

    return ft.Column([
        nav_bar(state, navigate, "vendor"),
        ft.Container(
            content=ft.Column([
                ft.Text("Vendor dashboard", size=22, weight=ft.FontWeight.BOLD),
                ft.Text("Create a listing", size=16, weight=ft.FontWeight.BOLD),
                ft.Row([title_field, category_field]),
                description_field,
                ft.Row([price_field, quantity_field]),
                photo_fields_column,
                ft.TextButton(content="+ Add another photo (up to 5)", on_click=add_photo_field),
                ft.ElevatedButton(content="Publish listing", on_click=create_listing),
                create_status,
                ft.Divider(),
                ft.Text("My listings", size=16, weight=ft.FontWeight.BOLD),
                listings_column,
                ft.Divider(),
                ft.Row([ft.Text("Incoming orders", size=16, weight=ft.FontWeight.BOLD),
                        ft.IconButton(icon=ft.Icons.REFRESH, on_click=load_orders)]),
                orders_column,
            ], spacing=12),
            padding=24,
        ),
    ], scroll=ft.ScrollMode.AUTO)
