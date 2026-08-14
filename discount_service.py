"""Discount service for the fashion e-commerce scenario in PROBLEM_STATEMENT.md.

Stacking order (per the assignment's docstring contract):
    1. Brand-specific discounts (per item, across categories)
    2. Category-specific discounts (per item)
    3. Voucher / coupon codes (per item, subject to exclusions)
    4. Bank card offers (cart-level, on the post-discount subtotal)

`CustomerProfile` is not defined in the assignment's data models (it is used
in the service interface but never declared) — it is added here, minimal,
to satisfy the given method signatures.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Data models (given by the assignment, treated as black boxes)
# ---------------------------------------------------------------------------

class BrandTier(Enum):
    PREMIUM = "premium"
    REGULAR = "regular"
    BUDGET = "budget"


@dataclass
class Product:
    id: str
    brand: str
    brand_tier: BrandTier
    category: str
    base_price: Decimal
    current_price: Decimal  # After brand/category discount


@dataclass
class CartItem:
    product: Product
    quantity: int
    size: str


@dataclass
class PaymentInfo:
    method: str  # CARD, UPI, etc
    bank_name: Optional[str]
    card_type: Optional[str]  # CREDIT, DEBIT


@dataclass
class DiscountedPrice:
    original_price: Decimal
    final_price: Decimal
    applied_discounts: Dict[str, Decimal]  # discount_name -> amount
    message: str


# ---------------------------------------------------------------------------
# CustomerProfile — undefined in the doc, added minimally (see module docstring)
# ---------------------------------------------------------------------------

class CustomerTier(Enum):
    NEW = "new"
    REGULAR = "regular"
    VIP = "vip"


@dataclass
class CustomerProfile:
    id: str
    tier: CustomerTier


# ---------------------------------------------------------------------------
# Discount rules — one class per discount type, so adding a new discount type
# means adding a new rule class, not touching DiscountService.
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

TWO_PLACES = Decimal("0.01")


def _round(amount: Decimal) -> Decimal:
    return amount.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


class DiscountService:
    """Applies brand/category/voucher/bank discounts in that order.

    Rule catalogs default to the assignment's dummy scenario so the class
    works out of the box, but can be overridden for other scenarios/tests.
    """

    def __init__(
        self,
        brand_rules: Optional[List[BrandDiscountRule]] = None,
        category_rules: Optional[List[CategoryDiscountRule]] = None,
        voucher_rules: Optional[List[VoucherRule]] = None,
        bank_rules: Optional[List[BankOfferRule]] = None,
    ) -> None:
        self.brand_rules = brand_rules if brand_rules is not None else [
            BrandDiscountRule(brand="PUMA", percent=Decimal("40")),
        ]
        self.category_rules = category_rules if category_rules is not None else [
            CategoryDiscountRule(category="T-shirts", percent=Decimal("10")),
        ]
        self.voucher_rules = voucher_rules if voucher_rules is not None else [
            VoucherRule(code="SUPER69", percent=Decimal("69")),
        ]
        self.bank_rules = bank_rules if bank_rules is not None else [
            BankOfferRule(bank_name="ICICI", percent=Decimal("10")),
        ]

    def _find_voucher(self, code: str) -> Optional[VoucherRule]:
        return next((v for v in self.voucher_rules if v.code.lower() == code.lower()), None)

    async def calculate_cart_discounts(
        self,
        cart_items: List[CartItem],
        customer: CustomerProfile,
        payment_info: Optional[PaymentInfo] = None,
        voucher_code: Optional[str] = None,
    ) -> DiscountedPrice:
        """
        Calculate final price after applying discount logic:
        - First apply brand/category discounts
        - Then apply coupon codes
        - Then apply bank offers

        `voucher_code` is optional and not part of the assignment's given
        signature (which has no way to pass a code in) — added so the
        "coupon codes" stacking stage is actually reachable. See README.
        """
        original_price = _round(
            sum((item.product.base_price * item.quantity for item in cart_items), Decimal("0"))
        )

        applied_discounts: Dict[str, Decimal] = {}
        messages: List[str] = []
        subtotal = Decimal("0")

        for item in cart_items:
            line_price = item.product.base_price * item.quantity

            for rule in self.brand_rules:
                if rule.applies_to(item):
                    discount_amount = line_price * rule.percent_off(item) / Decimal("100")
                    line_price -= discount_amount
                    applied_discounts[rule.name] = applied_discounts.get(rule.name, Decimal("0")) + discount_amount

            for rule in self.category_rules:
                if rule.applies_to(item):
                    discount_amount = line_price * rule.percent_off(item) / Decimal("100")
                    line_price -= discount_amount
                    applied_discounts[rule.name] = applied_discounts.get(rule.name, Decimal("0")) + discount_amount

            if voucher_code:
                voucher = self._find_voucher(voucher_code)
                if voucher and voucher.applies_to(item):
                    discount_amount = line_price * voucher.percent / Decimal("100")
                    line_price -= discount_amount
                    applied_discounts[voucher.name] = applied_discounts.get(voucher.name, Decimal("0")) + discount_amount

            subtotal += line_price

        if voucher_code:
            voucher = self._find_voucher(voucher_code)
            if not voucher:
                messages.append(f"Voucher {voucher_code} does not exist")
            else:
                ok, reason = voucher.eligibility(cart_items, customer)
                messages.append(reason if ok else reason)

        if payment_info:
            for rule in self.bank_rules:
                if rule.applies_to(payment_info):
                    discount_amount = subtotal * rule.percent / Decimal("100")
                    subtotal -= discount_amount
                    applied_discounts[rule.name] = applied_discounts.get(rule.name, Decimal("0")) + discount_amount

        final_price = _round(subtotal)
        applied_discounts = {name: _round(amount) for name, amount in applied_discounts.items()}

        if not messages:
            messages.append(
                f"Applied {len(applied_discounts)} discount(s)" if applied_discounts else "No discounts applied"
            )

        return DiscountedPrice(
            original_price=original_price,
            final_price=final_price,
            applied_discounts=applied_discounts,
            message="; ".join(messages),
        )

    async def validate_discount_code(
        self,
        code: str,
        cart_items: List[CartItem],
        customer: CustomerProfile,
    ) -> bool:
        """
        Validate if a discount code can be applied.
        Handle e-commerce-specific cases like:
        - Brand exclusions
        - Category restrictions
        - Customer tier requirements
        """
        voucher = self._find_voucher(code)
        if not voucher:
            return False
        ok, _reason = voucher.eligibility(cart_items, customer)
        return ok
