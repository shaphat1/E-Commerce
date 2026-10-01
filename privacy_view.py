import json

import flet as ft

import api_client
from components import nav_bar, error_banner


def build(state, page, navigate):
    if not state.logged_in:
        navigate("login")
        return ft.Column([])

    interactions_column = ft.Column([])
    status_text = ft.Text("")
    export_text = ft.Text("", selectable=True, size=11)

    def load_interactions(e=None):
        interactions_column.controls.clear()
        try:
            items = api_client.get_my_interactions(state)
        except api_client.ApiError as err:
            interactions_column.controls.append(error_banner(str(err)))
            page.update()
            return
        if not items:
            interactions_column.controls.append(ft.Text("Nothing recorded yet.", italic=True))
        for i in items:
            interactions_column.controls.append(
                ft.Text(f"{i['type']} -- {i['listing_title']}", size=13)
            )
        page.update()

    def do_export(e):
        try:
            data = api_client.export_my_data(state)
        except api_client.ApiError as err:
            status_text.value = str(err)
            status_text.color = ft.Colors.RED
            page.update()
            return
        export_text.value = json.dumps(data, indent=2)
        page.update()

    def do_clear_interactions(e):
        try:
            result = api_client.clear_my_interactions(state)
        except api_client.ApiError as err:
            status_text.value = str(err)
            status_text.color = ft.Colors.RED
            page.update()
            return
        status_text.value = f"Cleared {result['cleared']} recorded interaction(s)."
        status_text.color = ft.Colors.GREEN_800
        load_interactions()

    def do_delete_account(e):
        try:
            api_client.delete_my_account(state)
        except api_client.ApiError as err:
            status_text.value = str(err)
            status_text.color = ft.Colors.RED
            page.update()
            return
        state.logout()
        navigate("home")

    load_interactions()

    return ft.Column([
        nav_bar(state, navigate, "privacy"),
        ft.Container(
            content=ft.Column([
                ft.Text("Privacy & your data", size=22, weight=ft.FontWeight.BOLD),
                ft.Text(
                    "MAUMart processes your data under Nigeria's NDPA 2023. "
                    "See the full privacy policy for details -- this page is where you exercise your rights.",
                    size=13, color=ft.Colors.OUTLINE,
                ),
                ft.Divider(),
                ft.Text("What's feeding your recommendations", size=16, weight=ft.FontWeight.BOLD),
                interactions_column,
                ft.OutlinedButton(content="Clear my recommendation history", on_click=do_clear_interactions),
                ft.Divider(),
                ft.Text("Export your data", size=16, weight=ft.FontWeight.BOLD),
                ft.Text("Everything MAUMart holds about you, in one place (NDPA access + portability right).", size=12),
                ft.ElevatedButton(content="Export my data", on_click=do_export),
                ft.Container(
                    content=export_text, padding=8, bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                    border_radius=6, width=500,
                ),
                ft.Divider(),
                ft.Text("Delete your account", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.RED),
                ft.Text(
                    "Your name, email, and phone number are anonymized immediately and every "
                    "device you're logged into is signed out. Order and review records are kept "
                    "in anonymized form for legal/audit purposes -- see the privacy policy for why.",
                    size=12,
                ),
                ft.ElevatedButton(
                    content="Delete my account", on_click=do_delete_account,
                    style=ft.ButtonStyle(bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE),
                ),
                status_text,
            ], spacing=12),
            padding=24, width=560,
        ),
    ], scroll=ft.ScrollMode.AUTO)
