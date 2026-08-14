"""Dummy data for the 'Multiple Discount Scenario' in PROBLEM_STATEMENT.md:

    - PUMA T-shirt with "Min 40% off"
    - Additional 10% off on T-shirts category
    - ICICI bank offer of 10% instant discount
"""

from decimal import Decimal

from discount_service import (
    BrandTier,
    CartItem,
    CustomerProfile,
    CustomerTier,
    PaymentInfo,
    Product,
)

puma_tshirt = Product(
    id="prod-puma-tshirt-001",
    brand="PUMA",
    brand_tier=BrandTier.PREMIUM,
    category="T-shirts",
    base_price=Decimal("1500.00"),
    current_price=Decimal("1500.00"),
)

cart_items = [
    CartItem(product=puma_tshirt, quantity=1, size="M"),
]

customer = CustomerProfile(id="cust-001", tier=CustomerTier.REGULAR)

payment_info = PaymentInfo(method="CARD", bank_name="ICICI", card_type="CREDIT")
