"""Discount rules — one class per discount type, so adding a new discount
type means adding a new rule class, not touching DiscountService.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional

from enums import CustomerTier
from models import CartItem, CustomerProfile, PaymentInfo


class DiscountRule(ABC):
    name: str

    @abstractmethod
    def applies_to(self, item: CartItem) -> bool:
        """Whether this rule applies to a given cart item."""

    @abstractmethod
    def percent_off(self, item: CartItem) -> Decimal:
        """Percent (0-100) to take off this item's price."""


@dataclass
class BrandDiscountRule(DiscountRule):
    brand: str
    percent: Decimal
    name: str = field(init=False)

    def __post_init__(self) -> None:
        self.name = f"Min {self.percent}% off on {self.brand}"

    def applies_to(self, item: CartItem) -> bool:
        return item.product.brand.lower() == self.brand.lower()

    def percent_off(self, item: CartItem) -> Decimal:
        return self.percent


@dataclass
class CategoryDiscountRule(DiscountRule):
    category: str
    percent: Decimal
    name: str = field(init=False)

    def __post_init__(self) -> None:
        self.name = f"Extra {self.percent}% off on {self.category}"

    def applies_to(self, item: CartItem) -> bool:
        return item.product.category.lower() == self.category.lower()

    def percent_off(self, item: CartItem) -> Decimal:
        return self.percent


@dataclass
class BankOfferRule:
    bank_name: str
    percent: Decimal
    name: str = field(init=False)

    def __post_init__(self) -> None:
        self.name = f"{self.percent}% instant discount on {self.bank_name} cards"

    def applies_to(self, payment_info: Optional[PaymentInfo]) -> bool:
        return bool(
            payment_info
            and payment_info.bank_name
            and payment_info.bank_name.lower() == self.bank_name.lower()
        )


@dataclass
class VoucherRule:
    code: str
    percent: Decimal
    excluded_brands: List[str] = field(default_factory=list)
    allowed_categories: Optional[List[str]] = None
    min_tier: Optional[CustomerTier] = None
    name: str = field(init=False)

    def __post_init__(self) -> None:
        self.name = f"Voucher {self.code} ({self.percent}% off)"

    _TIER_RANK = {CustomerTier.NEW: 0, CustomerTier.REGULAR: 1, CustomerTier.VIP: 2}

    def eligibility(self, cart_items: List[CartItem], customer: CustomerProfile) -> tuple[bool, str]:
        if self.min_tier and self._TIER_RANK[customer.tier] < self._TIER_RANK[self.min_tier]:
            return False, f"Voucher {self.code} requires {self.min_tier.value} tier or above"

        eligible_items = [item for item in cart_items if self.applies_to(item)]
        if not eligible_items:
            return False, f"Voucher {self.code} does not apply to any item in the cart"

        return True, f"Voucher {self.code} applied"

    def applies_to(self, item: CartItem) -> bool:
        if item.product.brand.lower() in (b.lower() for b in self.excluded_brands):
            return False
        if self.allowed_categories and item.product.category.lower() not in (
            c.lower() for c in self.allowed_categories
        ):
            return False
        return True
