"""Discount service for the fashion e-commerce scenario in PROBLEM_STATEMENT.md.

Stacking order (per the assignment's docstring contract):
    1. Brand-specific discounts (per item, across categories)
    2. Category-specific discounts (per item)
    3. Voucher / coupon codes (per item, subject to exclusions)
    4. Bank card offers (cart-level, on the post-discount subtotal)
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Dict, List, Optional

from models import CartItem, CustomerProfile, DiscountedPrice, PaymentInfo
from rules import BankOfferRule, BrandDiscountRule, CategoryDiscountRule, VoucherRule

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
                _ok, reason = voucher.eligibility(cart_items, customer)
                messages.append(reason)

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
