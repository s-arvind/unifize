"""Discount service. Rules are read from core.db (entity DISCOUNT_RULES), not hardcoded.

Stacking order: brand/category (per item) -> voucher (per item) -> bank offer (cart subtotal).
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Callable, Dict, List, Optional

from core.db import InMemoryDB
from core.db import db as default_db
from enums import DiscountType
from models import DISCOUNT_RULES, CartItem, CustomerProfile, DiscountedPrice, DiscountRule, PaymentInfo


def _percent_of(amount: int, percent: Decimal) -> int:
    """amount * percent / 100 in paisa, rounded half up, capped at `amount` (a >100% rule can't go negative)."""
    raw = int((Decimal(amount) * percent / Decimal(100)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return min(raw, amount)


def _best_match(rules: List[DiscountRule], matches: Callable[[DiscountRule], bool]) -> Optional[DiscountRule]:
    """Highest-percent matching rule — same-type matches don't stack."""
    candidates = [rule for rule in rules if matches(rule)]
    return max(candidates, key=lambda rule: rule.percent, default=None)


class DiscountService:
    """Reads its rule catalog from core.db fresh on every call."""

    def __init__(self, db: Optional[InMemoryDB] = None) -> None:
        self.db = db or default_db

    def _rules(self, discount_type: DiscountType) -> List[DiscountRule]:
        return [rule for rule in self.db.find(DISCOUNT_RULES) if rule.type is discount_type]

    def _find_voucher(self, code: str) -> Optional[DiscountRule]:
        return next(
            (rule for rule in self._rules(DiscountType.VOUCHER) if rule.code.lower() == code.lower()), None
        )

    async def calculate_cart_discounts(
        self,
        cart_items: List[CartItem],
        customer: CustomerProfile,
        payment_info: Optional[PaymentInfo] = None,
        voucher_code: Optional[str] = None,
    ) -> DiscountedPrice:
        original_price = sum(item.product.base_price * item.quantity for item in cart_items)

        applied_discounts: Dict[str, int] = {}
        messages: List[str] = []
        subtotal = 0

        voucher = self._find_voucher(voucher_code) if voucher_code else None
        if voucher_code and not voucher:
            messages.append(f"Voucher {voucher_code} does not exist")
        elif voucher:
            _ok, reason = voucher.eligibility(cart_items, customer)
            messages.append(reason)

        brand_rules = self._rules(DiscountType.BRAND)
        category_rules = self._rules(DiscountType.CATEGORY)
        bank_rules = self._rules(DiscountType.BANK_OFFER)

        for item in cart_items:
            line_price = item.product.base_price * item.quantity

            best_brand = _best_match(brand_rules, lambda rule, item=item: rule.applies_to_item(item))
            best_category = _best_match(category_rules, lambda rule, item=item: rule.applies_to_item(item))

            for rule in (best_brand, best_category):
                if rule:
                    discount_amount = _percent_of(line_price, rule.percent)
                    line_price -= discount_amount
                    applied_discounts[rule.name] = applied_discounts.get(rule.name, 0) + discount_amount

            if voucher and voucher.applies_to_item(item):
                discount_amount = _percent_of(line_price, voucher.percent)
                line_price -= discount_amount
                applied_discounts[voucher.name] = applied_discounts.get(voucher.name, 0) + discount_amount

            subtotal += line_price

        if payment_info:
            best_bank = _best_match(bank_rules, lambda rule: rule.applies_to_payment(payment_info))
            if best_bank:
                discount_amount = _percent_of(subtotal, best_bank.percent)
                subtotal -= discount_amount
                applied_discounts[best_bank.name] = applied_discounts.get(best_bank.name, 0) + discount_amount

        final_price = subtotal

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
        """Handles brand exclusions, category restrictions, customer tier requirements."""
        voucher = self._find_voucher(code)
        if not voucher:
            return False
        ok, _reason = voucher.eligibility(cart_items, customer)
        return ok
