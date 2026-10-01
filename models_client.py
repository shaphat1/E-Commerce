"""
Small constants mirrored from backend/models.py so the Flet client can
render category pickers and know which order-status buttons to show
without importing the backend package (client and server are separate
deployables per the Section 8.2 architecture).
"""

CATEGORIES = [
    "Books & Study Materials",
    "Electronics & Gadgets",
    "Fashion & Accessories",
    "Groceries & Provisions",
    "Pharmacy & Health",
    "Food & Snacks",
    "Services",
    "Hostel & Room Essentials",
]

ORDER_STATUS_FLOW = {
    "pending_payment": ["confirmed_paid", "payment_failed"],
    "confirmed_paid": ["confirmed", "payment_failed"],
    "confirmed": ["ready_for_delivery"],
    "ready_for_delivery": ["completed"],
    "completed": [],
    "payment_failed": [],
}
