"""
In-memory app state for the current session: who's logged in, and what's
in their cart. Nothing here is persisted -- all durable data lives on the
backend (Section 8.1 ERD); this is purely client-side UI state.
"""
import os
from dataclasses import dataclass, field


@dataclass
class CartLine:
    listing_id: str
    title: str
    price: float
    vendor_name: str
    quantity: int = 1


@dataclass
class AppState:
    api_base: str = field(default_factory=lambda: os.environ.get("MAUMART_API_BASE", "http://127.0.0.1:8000"))
    token: str | None = None
    user_id: str | None = None
    name: str | None = None
    role: str | None = None  # buyer | vendor | admin
    cart: list[CartLine] = field(default_factory=list)

    @property
    def logged_in(self) -> bool:
        return self.token is not None

    def logout(self):
        self.token = None
        self.user_id = None
        self.name = None
        self.role = None
        self.cart = []

    def cart_total(self) -> float:
        return sum(line.price * line.quantity for line in self.cart)

    def add_to_cart(self, listing_id, title, price, vendor_name, quantity=1):
        for line in self.cart:
            if line.listing_id == listing_id:
                line.quantity += quantity
                return
        self.cart.append(CartLine(listing_id, title, price, vendor_name, quantity))

    def remove_from_cart(self, listing_id):
        self.cart = [l for l in self.cart if l.listing_id != listing_id]
