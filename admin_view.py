import flet as ft

import api_client
from components import nav_bar, error_banner


def build(state, page, navigate):
    if not state.logged_in or state.role != "admin":
        navigate("home")
        return ft.Column([])

    vendors_column = ft.Column([], spacing=8)
    listings_column = ft.Column([], spacing=8)
    disputes_column = ft.Column([], spacing=8)
    stats_row = ft.Row([], spacing=24)

    def load_all(e=None):
        load_vendors()
        load_listings()
        load_disputes()
        load_stats()

    def load_vendors():
        vendors_column.controls.clear()
        try:
            vendors = api_client.pending_vendors(state)
        except api_client.ApiError as err:
            vendors_column.controls.append(error_banner(str(err)))
            page.update()
            return
        if not vendors:
            vendors_column.controls.append(ft.Text("No vendors awaiting verification.", italic=True))
        for v in vendors:
            def make_approve(vendor_id):
                def handler(e):
                    try:
                        api_client.approve_vendor(state, vendor_id)
                    except api_client.ApiError as err:
                        vendors_column.controls.append(error_banner(str(err)))
                        page.update()
                        return
                    load_vendors()
                return handler
            vendors_column.controls.append(ft.Row([
                ft.Text(f"{v['business_name']} ({v['category']})", expand=True),
                ft.ElevatedButton(content="Approve", on_click=make_approve(v["id"])),
            ]))
        page.update()

    def load_listings():
        listings_column.controls.clear()
        try:
            listings = api_client.pending_listings(state)
        except api_client.ApiError as err:
            listings_column.controls.append(error_banner(str(err)))
            page.update()
            return
        if not listings:
            listings_column.controls.append(ft.Text("No listings awaiting review.", italic=True))
        for l in listings:
            def make_approve(listing_id):
                def handler(e):
                    try:
                        api_client.approve_listing(state, listing_id)
                    except api_client.ApiError as err:
                        listings_column.controls.append(error_banner(str(err)))
                        page.update()
                        return
                    load_listings()
                return handler
            listings_column.controls.append(ft.Row([
                ft.Text(f"{l['title']} -- {l['category']} (by {l['vendor']})", expand=True),
                ft.ElevatedButton(content="Approve", on_click=make_approve(l["id"])),
            ]))
        page.update()

    def load_disputes():
        disputes_column.controls.clear()
        try:
            disputes = api_client.open_disputes(state)
        except api_client.ApiError as err:
            disputes_column.controls.append(error_banner(str(err)))
            page.update()
            return
        if not disputes:
            disputes_column.controls.append(ft.Text("No open disputes.", italic=True))
        for d in disputes:
            def make_resolve(dispute_id, refund):
                def handler(e):
                    try:
                        api_client.resolve_dispute(state, dispute_id, refund)
                    except api_client.ApiError as err:
                        disputes_column.controls.append(error_banner(str(err)))
                        page.update()
                        return
                    load_disputes()
                return handler
            disputes_column.controls.append(ft.Row([
                ft.Text(d["reason"] or "(no reason given)", expand=True),
                ft.ElevatedButton(content="Refund buyer", on_click=make_resolve(d["id"], True)),
                ft.OutlinedButton(content="Close, no refund", on_click=make_resolve(d["id"], False)),
            ]))
        page.update()

    def load_stats():
        try:
            stats = api_client.platform_stats(state)
        except api_client.ApiError as err:
            stats_row.controls = [error_banner(str(err))]
            page.update()
            return

        def stat_card(label, value):
            return ft.Container(
                content=ft.Column([
                    ft.Text(str(value), size=24, weight=ft.FontWeight.BOLD),
                    ft.Text(label, size=12, color=ft.Colors.OUTLINE),
                ]),
                padding=16, border_radius=10, border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT), width=160,
            )

        stats_row.controls = [
            stat_card("Active vendors", stats["active_vendors"]),
            stat_card("Active buyers", stats["active_buyers"]),
            stat_card("Live listings", stats["live_listings"]),
            stat_card("GMV (₦)", f"{stats['gmv']:,.0f}"),
        ]
        page.update()

    load_all()

    return ft.Column([
        nav_bar(state, navigate, "admin"),
        ft.Container(
            content=ft.Column([
                ft.Row([ft.Text("Admin dashboard", size=22, weight=ft.FontWeight.BOLD),
                        ft.IconButton(icon=ft.Icons.REFRESH, on_click=load_all)]),
                stats_row,
                ft.Divider(),
                ft.Text("Vendors pending verification", size=16, weight=ft.FontWeight.BOLD),
                vendors_column,
                ft.Divider(),
                ft.Text("Listings pending review (restricted categories)", size=16, weight=ft.FontWeight.BOLD),
                listings_column,
                ft.Divider(),
                ft.Text("Open disputes", size=16, weight=ft.FontWeight.BOLD),
                disputes_column,
            ], spacing=12),
            padding=24,
        ),
    ], scroll=ft.ScrollMode.AUTO)
