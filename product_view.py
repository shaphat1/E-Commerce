import flet as ft

import api_client
from components import nav_bar, error_banner


def build(state, page, navigate, listing_id):
    try:
        listing = api_client.get_listing(state, listing_id)
    except api_client.ApiError as err:
        return ft.Column([nav_bar(state, navigate, "home"), error_banner(str(err))])

    api_client.log_view(state, listing_id)  # FR-7.2/7.3 signal

    try:
        review_data = api_client.vendor_reviews(state, listing["vendor_id"])
    except api_client.ApiError:
        review_data = {"average_rating": None, "count": 0, "reviews": []}

    qty_field = ft.TextField(label="Quantity", value="1", width=100)
    status_text = ft.Text("")

    def add_to_cart(e):
        try:
            qty = max(1, int(qty_field.value))
        except ValueError:
            qty = 1
        if listing["quantity"] < qty:
            status_text.value = "Not enough stock available."
            status_text.color = ft.Colors.RED
            page.update()
            return
        state.add_to_cart(listing["id"], listing["title"], listing["price"], listing["vendor_name"], qty)
        status_text.value = "Added to cart."
        status_text.color = ft.Colors.GREEN_800
        page.update()

    photo = (listing.get("photo_urls") or [None])[0]
    rating_text = (
        f"{review_data['average_rating']} / 5 ({review_data['count']} review(s))"
        if review_data["average_rating"] is not None else "No reviews yet"
    )

    reviews_column = ft.Column([
        ft.Text(f"{r['rating']}/5 -- {r['comment']}") for r in review_data["reviews"]
    ])

    return ft.Column([
        nav_bar(state, navigate, "home"),
        ft.Container(
            content=ft.Column([
                ft.TextButton(content="< Back to browse", on_click=lambda e: navigate("home")),
                ft.Row([
                    ft.Container(
                        content=ft.Image(src=photo, width=280, height=280, fit=ft.BoxFit.COVER)
                        if photo else ft.Icon(ft.Icons.SHOPPING_BAG, size=100),
                        width=300, height=300, alignment=ft.Alignment.CENTER,
                        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT), border_radius=12,
                    ),
                    ft.Column([
                        ft.Text(listing["title"], size=24, weight=ft.FontWeight.BOLD),
                        ft.Text(f"Sold by {listing['vendor_name']}", color=ft.Colors.OUTLINE),
                        ft.Text(f"Vendor rating: {rating_text}", size=13),
                        ft.Text(f"₦{listing['price']:,.0f}", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_800),
                        ft.Text(f"{listing['quantity']} in stock", size=13, color=ft.Colors.OUTLINE),
                        ft.Text(listing["description"], size=14),
                        ft.Row([qty_field, ft.ElevatedButton(content="Add to cart", on_click=add_to_cart)]),
                        status_text,
                    ], spacing=8, expand=True),
                ], spacing=24, vertical_alignment=ft.CrossAxisAlignment.START),
                ft.Divider(),
                ft.Text("Reviews", size=18, weight=ft.FontWeight.BOLD),
                reviews_column if review_data["reviews"] else ft.Text("No reviews yet.", italic=True),
            ], spacing=16),
            padding=24,
        ),
    ], scroll=ft.ScrollMode.AUTO)
