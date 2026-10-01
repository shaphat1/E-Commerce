"""
Seeds the database with demo data so the app is usable/testable immediately:
one admin, six approved vendors (one per non-pharmacy category, plus a
pharmacy vendor for the restricted-category demo), a spread of listings,
three buyers, some interaction/order history (so all three recommendation
tiers -- trending, content-based, collaborative filtering -- have something
to show), and a couple of reviews.

Run once: `python seed.py` (safe to re-run -- it wipes and recreates the DB).
"""
import os
import sys
from datetime import datetime, timezone, timedelta

import config
from database import engine, Base, SessionLocal, DATABASE_URL, init_db
import models
from auth_utils import hash_password

# DESTRUCTIVE: this script wipes the database. It has publicly documented demo
# passwords, so it must never touch a production system. (docker-compose used to run
# it on every container start, which would have erased all data on each restart.)
if config.is_production():
    sys.exit("Refusing to run seed.py with MAUMART_ENV=production (it wipes the database "
             "and creates accounts with public demo passwords). Use create_admin.py instead.")
if not DATABASE_URL.startswith("sqlite") and os.environ.get("MAUMART_SEED_CONFIRM") != "yes":
    sys.exit("seed.py DROPS ALL TABLES in the target database.\n"
             f"Target: {engine.url.render_as_string(hide_password=True)}\n"
             "Re-run with MAUMART_SEED_CONFIRM=yes if that is really what you want.")

if DATABASE_URL.startswith("sqlite"):
    db_file = DATABASE_URL.replace("sqlite:///", "")
    if os.path.exists(db_file):
        os.remove(db_file)
else:
    Base.metadata.drop_all(bind=engine)
init_db()

db = SessionLocal()


def make_user(name, email, phone, password, role, status="active"):
    u = models.User(name=name, email=email, phone=phone,
                     password_hash=hash_password(password), role=role, status=status,
                     email_verified=True, agreed_to_terms=True)
    db.add(u)
    db.flush()
    return u


def make_vendor(user, business_name, category):
    v = models.Vendor(user_id=user.id, business_name=business_name,
                       category=category, verification_status="approved")
    db.add(v)
    db.flush()
    return v


def make_listing(vendor, title, category, description, price, quantity, photo_url, sales_count=0):
    l = models.Listing(vendor_id=vendor.id, title=title, category=category,
                        description=description, price=price, quantity=quantity,
                        status="live", sales_count=sales_count)
    db.add(l)
    db.flush()
    db.add(models.ListingPhoto(listing_id=l.id, url=photo_url))
    return l


# ---------- Admin ----------
admin = make_user("MAUMart Admin", "admin@maumart.ng", "+2348000000000", "AdminPass1", "admin")

# ---------- Vendors ----------
v_books_user = make_user("Ibrahim Yusuf", "ibrahim.books@maumart.ng", "+2348011111111", "VendorPass1", "vendor", status="active")
v_books = make_vendor(v_books_user, "Adama Books & Stationery", "Books & Study Materials")

v_elec_user = make_user("Chidi Okafor", "chidi.gadgets@maumart.ng", "+2348022222222", "VendorPass1", "vendor")
v_elec = make_vendor(v_elec_user, "Yola Gadget Hub", "Electronics & Gadgets")

v_fashion_user = make_user("Hauwa Bello", "hauwa.fashion@maumart.ng", "+2348033333333", "VendorPass1", "vendor")
v_fashion = make_vendor(v_fashion_user, "Chiroma Fashion Point", "Fashion & Accessories")

v_grocery_user = make_user("Samuel Danladi", "samuel.grocery@maumart.ng", "+2348044444444", "VendorPass1", "vendor")
v_grocery = make_vendor(v_grocery_user, "Girei Provisions Store", "Groceries & Provisions")

v_food_user = make_user("Blessing Amos", "blessing.food@maumart.ng", "+2348055555555", "VendorPass1", "vendor")
v_food = make_vendor(v_food_user, "Campus Bites", "Food & Snacks")

v_pharma_user = make_user("Fatima Aliyu", "fatima.pharmacy@maumart.ng", "+2348066666666", "VendorPass1", "vendor")
v_pharma = make_vendor(v_pharma_user, "Yola Health Point", "Pharmacy & Health")

# ---------- Listings ----------
physics_book = make_listing(v_books, "University Physics Textbook (3rd Ed)", "Books & Study Materials",
                             "Comprehensive physics textbook covering CSC/PHY 100-level courses.",
                             8500, 12, "https://picsum.photos/seed/physics/400", sales_count=14)
calc_book = make_listing(v_books, "Scientific Calculator (Casio FX-991)", "Books & Study Materials",
                          "Standard scientific calculator accepted for MAU exams.",
                          6200, 20, "https://picsum.photos/seed/calc/400", sales_count=22)
past_qs = make_listing(v_books, "CSC 100-Level Past Questions Bundle", "Books & Study Materials",
                        "Compiled past questions for first-year Computer Science courses.",
                        1500, 40, "https://picsum.photos/seed/pastq/400", sales_count=9)

power_bank = make_listing(v_elec, "20000mAh Power Bank", "Electronics & Gadgets",
                           "Fast-charging power bank, ideal for hostel use during outages.",
                           9500, 15, "https://picsum.photos/seed/powerbank/400", sales_count=18)
usb_drive = make_listing(v_elec, "64GB USB Flash Drive", "Electronics & Gadgets",
                          "USB 3.0 flash drive for assignments and project submissions.",
                          4200, 30, "https://picsum.photos/seed/usb/400", sales_count=11)
earpods = make_listing(v_elec, "Wireless Earbuds", "Electronics & Gadgets",
                        "Bluetooth earbuds with charging case.",
                        12000, 10, "https://picsum.photos/seed/earbuds/400", sales_count=7)

hoodie = make_listing(v_fashion, "MAU Branded Hoodie", "Fashion & Accessories",
                       "Comfortable cotton-blend hoodie with MAU crest print.",
                       7500, 25, "https://picsum.photos/seed/hoodie/400", sales_count=13)
sandals = make_listing(v_fashion, "Campus Slides/Sandals", "Fashion & Accessories",
                        "Durable everyday slides, several sizes available.",
                        3500, 30, "https://picsum.photos/seed/sandals/400", sales_count=6)

rice_bag = make_listing(v_grocery, "10kg Bag of Rice", "Groceries & Provisions",
                         "Locally sourced rice, 10kg bag.",
                         11000, 18, "https://picsum.photos/seed/rice/400", sales_count=10)
provisions_pack = make_listing(v_grocery, "Hostel Starter Provisions Pack", "Groceries & Provisions",
                                "Noodles, garri, seasoning cubes, and drinks bundle.",
                                6000, 22, "https://picsum.photos/seed/provisions/400", sales_count=15)

jollof = make_listing(v_food, "Jollof Rice & Chicken (Plate)", "Food & Snacks",
                       "Freshly prepared jollof rice with grilled chicken, campus delivery.",
                       1800, 50, "https://picsum.photos/seed/jollof/400", sales_count=31)
meat_pie = make_listing(v_food, "Meat Pie (Pack of 4)", "Food & Snacks",
                         "Freshly baked meat pies, pack of 4.",
                         1200, 40, "https://picsum.photos/seed/meatpie/400", sales_count=17)

toiletries = make_listing(v_pharma, "Toiletries Bundle (Soap, Toothpaste, Sanitizer)", "Pharmacy & Health",
                           "Basic hostel toiletries bundle -- OTC items only.",
                           3200, 25, "https://picsum.photos/seed/toiletries/400", sales_count=8)

db.commit()

# ---------- Buyers ----------
buyer1 = make_user("Amina Sule", "amina.sule@maumart.ng", "+2348077777777", "BuyerPass1", "buyer")
buyer2 = make_user("Emeka Nwosu", "emeka.nwosu@maumart.ng", "+2348088888888", "BuyerPass1", "buyer")
buyer3 = make_user("Ruth Philemon", "ruth.philemon@maumart.ng", "+2348099999999", "BuyerPass1", "buyer")
db.commit()


def make_completed_order(buyer, vendor, items, days_ago=3):
    """items: list of (listing, qty). Creates order + items + purchase interactions + marks completed."""
    import uuid
    session_id = str(uuid.uuid4())
    subtotal = sum(l.price * q for l, q in items)
    vat = round(subtotal * models.VAT_RATE, 2)
    total = round(subtotal + vat + 500, 2)
    created = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days_ago)
    order = models.Order(buyer_id=buyer.id, vendor_id=vendor.id, session_id=session_id,
                          subtotal=subtotal, vat_amount=vat, delivery_fee=500.0,
                          total=total, status="completed", payment_reference=f"SEED-{uuid.uuid4().hex[:8]}",
                          delivery_address="MAU Hostel Block C, Yola",
                          created_at=created, updated_at=created)
    db.add(order)
    db.flush()
    for listing, qty in items:
        db.add(models.OrderItem(order_id=order.id, listing_id=listing.id,
                                 quantity=qty, price_at_purchase=listing.price))
        db.add(models.Interaction(user_id=buyer.id, listing_id=listing.id, type="purchase",
                                   created_at=created))
    return order


# Buyer1 and buyer2 both bought physics book + calculator together -> strong CF signal.
o1 = make_completed_order(buyer1, v_books, [(physics_book, 1), (calc_book, 1)], days_ago=10)
o2 = make_completed_order(buyer2, v_books, [(physics_book, 1), (calc_book, 1)], days_ago=8)
# Buyer3 bought physics book + USB drive (from a different vendor, separate order per vendor).
o3a = make_completed_order(buyer3, v_books, [(physics_book, 1)], days_ago=6)
o3b = make_completed_order(buyer3, v_elec, [(usb_drive, 1)], days_ago=6)
# Some food + provisions orders for volume/variety.
o4 = make_completed_order(buyer1, v_food, [(jollof, 2)], days_ago=2)
o5 = make_completed_order(buyer2, v_grocery, [(provisions_pack, 1)], days_ago=4)
db.commit()

# Extra browsing (view) interactions for buyer1 so they clear the cold-start threshold
# and have a content-based/CF profile beyond their purchases.
view_targets = [power_bank, earpods, hoodie, past_qs, toiletries]
for listing in view_targets:
    db.add(models.Interaction(user_id=buyer1.id, listing_id=listing.id, type="view",
                               created_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)))
db.commit()

# ---------- Reviews on completed orders ----------
db.add(models.Review(order_id=o1.id, buyer_id=buyer1.id, vendor_id=v_books.id,
                      rating=5, comment="Fast delivery, book was in great condition."))
db.add(models.Review(order_id=o4.id, buyer_id=buyer1.id, vendor_id=v_food.id,
                      rating=4, comment="Tasty, arrived a little late."))
db.commit()

print("Seed complete.")
print("Admin login:   admin@maumart.ng / AdminPass1")
print("Vendor login:  ibrahim.books@maumart.ng / VendorPass1  (Adama Books & Stationery)")
print("Buyer login:   amina.sule@maumart.ng / BuyerPass1")
print(f"Listings seeded: {db.query(models.Listing).count()}")
print(f"Orders seeded:   {db.query(models.Order).count()}")

db.close()
