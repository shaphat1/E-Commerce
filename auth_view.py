import flet as ft

import api_client
from components import nav_bar, error_banner


def login_view(state, page, navigate):
    email = ft.TextField(label="Email", width=340)
    password = ft.TextField(label="Password", password=True, can_reveal_password=True, width=340)
    error_text = ft.Ref[ft.Container]()

    def do_login(e):
        try:
            result = api_client.login(state, email.value.strip(), password.value)
        except api_client.ApiError as err:
            error_text.current.content = error_banner(str(err)).content
            error_text.current.bgcolor = ft.Colors.ERROR_CONTAINER
            page.update()
            return
        state.token = result["token"]
        state.user_id = result["user_id"]
        state.name = result["name"]
        state.role = result["role"]
        navigate("home")

    return ft.Column([
        nav_bar(state, navigate, "login"),
        ft.Container(
            content=ft.Column([
                ft.Text("Log in to MAUMart", size=22, weight=ft.FontWeight.BOLD),
                email, password,
                ft.Container(ref=error_text, height=0),
                ft.ElevatedButton(content="Log in", on_click=do_login, width=340),
                ft.TextButton(content="No account? Register", on_click=lambda e: navigate("register")),
                ft.Text("Demo logins -- buyer: amina.sule@maumart.ng / BuyerPass1  "
                        "vendor: ibrahim.books@maumart.ng / VendorPass1  "
                        "admin: admin@maumart.ng / AdminPass1", size=11, color=ft.Colors.OUTLINE),
            ], spacing=12, horizontal_alignment=ft.CrossAxisAlignment.START),
            padding=32, width=420,
        ),
    ])


def register_view(state, page, navigate):
    name = ft.TextField(label="Full name", width=340)
    email = ft.TextField(label="Email", width=340)
    phone = ft.TextField(label="Phone", width=340, hint_text="+234...")
    password = ft.TextField(label="Password", password=True, can_reveal_password=True, width=340,
                             hint_text="At least 8 characters, incl. a number")
    role = ft.Dropdown(
        label="Account type", width=340,
        options=[ft.dropdown.Option("buyer", "Buyer"), ft.dropdown.Option("vendor", "Vendor")],
        value="buyer",
    )
    business_name = ft.TextField(label="Business name", width=340, visible=False)
    vendor_category = ft.Dropdown(
        label="Category", width=340, visible=False,
        options=[ft.dropdown.Option(c) for c in [
            "Books & Study Materials", "Electronics & Gadgets", "Fashion & Accessories",
            "Groceries & Provisions", "Pharmacy & Health", "Food & Snacks",
            "Services", "Hostel & Room Essentials",
        ]],
    )
    agree_checkbox = ft.Checkbox(
        label="I agree to the Terms of Service, Vendor Agreement (if applicable), and Privacy Policy",
        value=False,
    )
    error_box = ft.Container(height=0)

    def on_role_change(e):
        is_vendor = role.value == "vendor"
        business_name.visible = is_vendor
        vendor_category.visible = is_vendor
        page.update()

    role.on_change = on_role_change

    def do_register(e):
        nonlocal error_box
        if not agree_checkbox.value:
            error_box.content = ft.Text(
                "You must agree to the Terms of Service and Privacy Policy to register.",
                color=ft.Colors.ON_ERROR_CONTAINER,
            )
            error_box.bgcolor = ft.Colors.ERROR_CONTAINER
            error_box.padding = 12
            error_box.border_radius = 8
            page.update()
            return
        try:
            result = api_client.register(
                state, name.value.strip(), email.value.strip(), phone.value.strip(), password.value,
                role.value, business_name.value.strip() or None, vendor_category.value,
                agree_checkbox.value,
            )
        except api_client.ApiError as err:
            error_box.content = ft.Text(str(err), color=ft.Colors.ON_ERROR_CONTAINER)
            error_box.bgcolor = ft.Colors.ERROR_CONTAINER
            error_box.padding = 12
            error_box.border_radius = 8
            page.update()
            return
        state.token = result["token"]
        state.user_id = result["user_id"]
        state.name = result["name"]
        state.role = result["role"]
        navigate("home")

    return ft.Column([
        nav_bar(state, navigate, "register"),
        ft.Container(
            content=ft.Column([
                ft.Text("Create an account", size=22, weight=ft.FontWeight.BOLD),
                name, email, phone, password, role, business_name, vendor_category,
                agree_checkbox,
                error_box,
                ft.ElevatedButton(content="Register", on_click=do_register, width=340),
                ft.Text(
                    "Vendor accounts require admin approval before you can list products.",
                    size=12, color=ft.Colors.OUTLINE,
                ),
            ], spacing=12, horizontal_alignment=ft.CrossAxisAlignment.START),
            padding=32, width=420,
        ),
    ])
