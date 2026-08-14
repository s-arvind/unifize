"""Populates core.db with the dummy scenario and discount rule catalog. Safe to call repeatedly — clears and re-inserts."""

from decimal import Decimal
from typing import List

from core.db import db
from enums import BrandTier, Category, CustomerTier, DiscountType
from models import DISCOUNT_RULES, CartItem, CustomerProfile, DiscountRule, PaymentInfo, Product

PRODUCTS = "products"
CART_ITEMS = "cart_items"
CUSTOMERS = "customers"
PAYMENT_INFOS = "payment_infos"


def seed() -> dict:
    for entity in (PRODUCTS, CART_ITEMS, CUSTOMERS, PAYMENT_INFOS, DISCOUNT_RULES):
        db.clear(entity)

    puma_tshirt = Product(
        id="prod-puma-tshirt-001",
        brand="PUMA",
        brand_tier=BrandTier.PREMIUM,
        category=Category.T_SHIRTS,
        base_price=150000,  # 1500.00 -> 150000 paisa
        current_price=150000,
    )
    db.insert(PRODUCTS, puma_tshirt.id, puma_tshirt)

    cart_item = CartItem(product=puma_tshirt, quantity=1, size="M")
    db.insert(CART_ITEMS, cart_item.id, cart_item)

    customer = CustomerProfile(id="cust-001", tier=CustomerTier.REGULAR)
    db.insert(CUSTOMERS, customer.id, customer)

    payment_info = PaymentInfo(method="CARD", bank_name="ICICI", card_type="CREDIT")
    db.insert(PAYMENT_INFOS, payment_info.id, payment_info)

    for rule in (
        DiscountRule(type=DiscountType.BRAND, percent=Decimal("40"), brand="PUMA"),
        DiscountRule(type=DiscountType.CATEGORY, percent=Decimal("10"), category=Category.T_SHIRTS),
        DiscountRule(type=DiscountType.VOUCHER, percent=Decimal("69"), code="SUPER69"),
        DiscountRule(type=DiscountType.BANK_OFFER, percent=Decimal("10"), bank_name="ICICI"),
    ):
        db.insert(DISCOUNT_RULES, rule.id, rule)

    cart_items: List[CartItem] = db.find(CART_ITEMS)

    return {
        "cart_items": cart_items,
        "customer": customer,
        "payment_info": payment_info,
    }


if __name__ == "__main__":
    seeded = seed()
    print(f"Seeded {len(seeded['cart_items'])} cart item(s) for customer {seeded['customer'].id}")
