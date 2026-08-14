"""Single discount model covering all discount types, discriminated by `type`."""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional, Tuple

from enums import Category, CustomerTier, DiscountType
from models.cart_item import CartItem
from models.customer_profile import CustomerProfile
from models.entity import Entity
from models.payment_info import PaymentInfo

DISCOUNT_RULES = "discount_rules"  # core.db entity name for DiscountRule records

_TIER_RANK = {CustomerTier.NEW: 0, CustomerTier.REGULAR: 1, CustomerTier.VIP: 2}


@dataclass(kw_only=True)
class DiscountRule(Entity):
    type: DiscountType
    percent: Decimal

    # DiscountType.BRAND
    brand: Optional[str] = None
    # DiscountType.CATEGORY
    category: Optional[Category] = None
    # DiscountType.VOUCHER
    code: Optional[str] = None
    excluded_brands: List[str] = field(default_factory=list)
    allowed_categories: Optional[List[Category]] = None
    min_tier: Optional[CustomerTier] = None
    # DiscountType.BANK_OFFER
    bank_name: Optional[str] = None

    @property
    def name(self) -> str:
        if self.type is DiscountType.BRAND:
            return f"Min {self.percent}% off on {self.brand}"
        if self.type is DiscountType.CATEGORY:
            return f"Extra {self.percent}% off on {self.category.value}"
        if self.type is DiscountType.VOUCHER:
            return f"Voucher {self.code} ({self.percent}% off)"
        return f"{self.percent}% instant discount on {self.bank_name} cards"

    def applies_to_item(self, item: CartItem) -> bool:
        if self.type is DiscountType.BRAND:
            return item.product.brand.lower() == self.brand.lower()

        if self.type is DiscountType.CATEGORY:
            return item.product.category == self.category

        if self.type is DiscountType.VOUCHER:
            if item.product.brand.lower() in (b.lower() for b in self.excluded_brands):
                return False
            if self.allowed_categories and item.product.category not in self.allowed_categories:
                return False
            return True

        return False

    def applies_to_payment(self, payment_info: Optional[PaymentInfo]) -> bool:
        return bool(
            self.type is DiscountType.BANK_OFFER
            and payment_info
            and payment_info.bank_name
            and payment_info.bank_name.lower() == self.bank_name.lower()
        )

    def eligibility(self, cart_items: List[CartItem], customer: CustomerProfile) -> Tuple[bool, str]:
        """Cart/customer-level eligibility for a voucher (type must be VOUCHER)."""
        if self.min_tier and _TIER_RANK[customer.tier] < _TIER_RANK[self.min_tier]:
            return False, f"Voucher {self.code} requires {self.min_tier.value} tier or above"

        if not any(self.applies_to_item(item) for item in cart_items):
            return False, f"Voucher {self.code} does not apply to any item in the cart"

        return True, f"Voucher {self.code} applied"
