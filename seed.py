"""Populates the in-memory db with the 'Multiple Discount Scenario' from
PROBLEM_STATEMENT.md:

    - PUMA T-shirt with "Min 40% off"
    - Additional 10% off on T-shirts category
    - ICICI bank offer of 10% instant discount

Replaces fake_data.py: instead of module-level objects, this writes
through core.db so the dummy scenario lives in the same store the rest
of the app reads from. Re-running seed() clears and re-inserts, so it's
safe to call repeatedly (e.g. once per test module).
"""

from decimal import Decimal
from typing import List

from core.db import db
from enums import BrandTier, CustomerTier
from models import CartItem, CustomerProfile, PaymentInfo, Product

PRODUCTS = "products"
CART_ITEMS = "cart_items"
CUSTOMERS = "customers"
PAYMENT_INFOS = "payment_infos"


def seed() -> dict:
    for entity in (PRODUCTS, CART_ITEMS, CUSTOMERS, PAYMENT_INFOS):
        db.clear(entity)

    puma_tshirt = Product(
        id="prod-puma-tshirt-001",
        brand="PUMA",
        brand_tier=BrandTier.PREMIUM,
        category="T-shirts",
        base_price=Decimal("1500.00"),
        current_price=Decimal("1500.00"),
    )
    db.insert(PRODUCTS, puma_tshirt.id, puma_tshirt)

    cart_item = CartItem(product=puma_tshirt, quantity=1, size="M")
    db.insert(CART_ITEMS, cart_item.id, cart_item)

    customer = CustomerProfile(id="cust-001", tier=CustomerTier.REGULAR)
    db.insert(CUSTOMERS, customer.id, customer)

    payment_info = PaymentInfo(method="CARD", bank_name="ICICI", card_type="CREDIT")
    db.insert(PAYMENT_INFOS, payment_info.id, payment_info)

    cart_items: List[CartItem] = db.find(CART_ITEMS)

    return {
        "cart_items": cart_items,
        "customer": customer,
        "payment_info": payment_info,
    }


if __name__ == "__main__":
    seeded = seed()
    print(f"Seeded {len(seeded['cart_items'])} cart item(s) for customer {seeded['customer'].id}")
