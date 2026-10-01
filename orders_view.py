import flet as ft

import api_client
from components import nav_bar, error_banner


def build(state, page, navigate):
    if not state.logged_in:
        navigate("login")
        return ft.Column([])

    root_list = ft.Column([], spacing=12)

    def load(e=None):
        root_list.controls.clear()
        try:
            orders = api_client.my_orders(state)
        except api_client.ApiError as err:
            root_list.controls.append(error_banner(str(err)))
            page.update()
            return

        if not orders:
            root_list.controls.append(ft.Text("You haven't placed any orders yet.", italic=True))
        for o in orders:
            root_list.controls.append(order_row(o))
        page.update()

    def order_row(o):
        rating_field = ft.Dropdown(
            width=100, options=[ft.dropdown.Option(str(i)) for i in range(1, 6)], value="5",
        )
        comment_field = ft.TextField(label="Comment", width=240)
        review_status = ft.Text("")

        def submit_review(order_id):
            def handler(e):
                try:
                    api_client.create_review(state, order_id, int(rating_field.value), comment_field.value)
                except api_client.ApiError as err:
                    review_status.value = str(err)
                    review_status.color = ft.Colors.RED
                else:
                    review_status.value = "Review submitted -- thank you!"
                    review_status.color = ft.Colors.GREEN_800
                page.update()
            return handler

        dispute_reason = ft.TextField(label="What went wrong?", width=280)
        dispute_status = ft.Text("")

        def submit_dispute(order_id):
            def handler(e):
                try:
                    api_client.raise_dispute(state, order_id, dispute_reason.value)
                except api_client.ApiError as err:
                    dispute_status.value = str(err)
                    dispute_status.color = ft.Colors.RED
                else:
                    dispute_status.value = "Reported to admin -- we'll follow up."
                    dispute_status.color = ft.Colors.GREEN_800
                page.update()
            return handler

        pay_status = ft.Text("")

        def check_payment(order):
            def handler(e):
                try:
                    api_client.verify_payment(state, order["payment_reference"])
                except api_client.ApiError as err:
                    pay_status.value, pay_status.color = str(err), ft.Colors.RED
                    page.update()
                    return
                load()
            return handler

        def cancel(order_id):
            def handler(e):
                try:
                    api_client.cancel_order(state, order_id)
                except api_client.ApiError as err:
                    pay_status.value, pay_status.color = str(err), ft.Colors.RED
                    page.update()
                    return
                load()
            return handler

        action_row = ft.Column([])
        if o["status"] == "pending_payment":
            buttons = []
            if o.get("payment_url"):
                buttons.append(ft.ElevatedButton(content="Pay now", url=o["payment_url"]))
            if o.get("payment_reference"):
                buttons.append(ft.OutlinedButton(content="I've paid -- check status", on_click=check_payment(o)))
            buttons.append(ft.TextButton(content="Cancel order", on_click=cancel(o["id"])))
            action_row.controls = [ft.Row(buttons, wrap=True), pay_status]
        elif o["status"] == "completed":
            action_row.controls = [
                ft.Text("Leave a review:", size=12),
                ft.Row([rating_field, comment_field, ft.ElevatedButton(content="Submit", on_click=submit_review(o["id"]))]),
                review_status,
            ]
        elif o["status"] not in ("payment_failed", "refunded"):
            action_row.controls = [
                ft.Row([dispute_reason, ft.OutlinedButton(content="Report an issue", on_click=submit_dispute(o["id"]))]),
                dispute_status,
            ]

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(o.get("vendor_name") or "Vendor", weight=ft.FontWeight.BOLD, expand=True),
                    ft.Text(f"₦{o['total']:,.0f}"),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Text(f"Status: {o['status']}", size=13, color=ft.Colors.BLUE_700),
                ft.Text(f"Delivery to: {o['delivery_address']}", size=12, color=ft.Colors.OUTLINE),
                action_row,
            ], spacing=6),
            padding=16, border_radius=10, border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT), width=480,
        )

    load()
    return ft.Column([
        nav_bar(state, navigate, "orders"),
        ft.Container(
            content=ft.Column([
                ft.Row([ft.Text("My orders", size=22, weight=ft.FontWeight.BOLD),
                        ft.IconButton(icon=ft.Icons.REFRESH, on_click=load)]),
                root_list,
            ], spacing=16),
            padding=24,
        ),
    ], scroll=ft.ScrollMode.AUTO)
