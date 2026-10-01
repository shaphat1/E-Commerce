import flet as ft

import api_client
from components import nav_bar, error_banner, listing_card

CATEGORIES = [
    "Books & Study Materials", "Electronics & Gadgets", "Fashion & Accessories",
    "Groceries & Provisions", "Pharmacy & Health", "Food & Snacks",
    "Services", "Hostel & Room Essentials",
]


def build(state, page, navigate):
    search_field = ft.TextField(label="Search MAUMart", width=340, hint_text="e.g. textbook, power bank")
    results_column = ft.Column([], spacing=12)
    error_msg = ft.Ref[ft.Text]()
    selected_category = {"value": None}

    def load_results():
        results_column.controls.clear()
        try:
            listings = api_client.browse_listings(
                state, category=selected_category["value"], q=search_field.value or None
            )
        except api_client.ApiError as err:
            results_column.controls.append(error_banner(str(err)))
            page.update()
            return

        if not listings:
            results_column.controls.append(ft.Text("No listings found.", italic=True))
        else:
            cards = [listing_card(l, navigate) for l in listings]
            results_column.controls.append(ft.Row(cards, wrap=True, spacing=12, run_spacing=12))
        page.update()

    def do_search(e):
        load_results()

    def pick_category(cat):
        def handler(e):
            selected_category["value"] = None if selected_category["value"] == cat else cat
            load_results()
        return handler

    category_chips = ft.Row(
        [ft.Chip(label=ft.Text(c), on_click=pick_category(c)) for c in CATEGORIES],
        wrap=True, spacing=8,
    )

    # ---- Recommended / trending section ----
    rec_column = ft.Column([ft.Text("Loading recommendations...", italic=True)])

    def load_recommendations():
        try:
            if state.logged_in:
                items = api_client.get_recommendations(state)
                heading = "Recommended for you"
            else:
                items = api_client.get_trending(state)
                heading = "Trending now"
        except api_client.ApiError as err:
            rec_column.controls = [error_banner(str(err))]
            page.update()
            return
        cards = [listing_card(l, navigate) for l in items[:8]]
        rec_column.controls = [
            ft.Text(heading, size=18, weight=ft.FontWeight.BOLD),
            ft.Row(cards, wrap=True, spacing=12, run_spacing=12) if cards else ft.Text("Nothing yet.", italic=True),
        ]
        page.update()

    load_results()
    load_recommendations()

    return ft.Column([
        nav_bar(state, navigate, "home"),
        ft.Container(
            content=ft.Column([
                ft.Row([search_field, ft.ElevatedButton(content="Search", on_click=do_search)]),
                category_chips,
                ft.Divider(),
                rec_column,
                ft.Divider(),
                ft.Text("Browse", size=18, weight=ft.FontWeight.BOLD),
                results_column,
            ], spacing=16),
            padding=24,
        ),
    ], scroll=ft.ScrollMode.AUTO)
