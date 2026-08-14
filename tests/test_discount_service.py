from decimal import Decimal

import pytest

from enums import DiscountType
from models import DiscountRule
from services.discount_service import DiscountService
from seed import seed

_seeded = seed()
cart_items = _seeded["cart_items"]
customer = _seeded["customer"]
payment_info = _seeded["payment_info"]


class _FakeDB:
    """Minimal db.find()-only stand-in, for testing rule selection in isolation
    from core.db's global singleton state."""

    def __init__(self, rules):
        self._rules = rules

    def find(self, entity):
        return self._rules


@pytest.mark.asyncio
async def test_multiple_discount_scenario_stacks_brand_category_and_bank_offer():
    service = DiscountService()

    result = await service.calculate_cart_discounts(
        cart_items=cart_items,
        customer=customer,
        payment_info=payment_info,
    )

    # base_price 150000 paisa -> 40% off (PUMA) -> 90000 -> 10% off (T-shirts) -> 81000
    # -> 10% off (ICICI bank offer, cart-level) -> 72900
    assert result.original_price == 150000
    assert result.final_price == 72900

    assert result.applied_discounts["Min 40% off on PUMA"] == 60000
    assert result.applied_discounts["Extra 10% off on T-shirts"] == 9000
    assert result.applied_discounts["10% instant discount on ICICI cards"] == 8100


@pytest.mark.asyncio
async def test_calculate_without_payment_info_skips_bank_offer():
    service = DiscountService()

    result = await service.calculate_cart_discounts(cart_items=cart_items, customer=customer)

    assert result.final_price == 81000
    assert "10% instant discount on ICICI cards" not in result.applied_discounts


@pytest.mark.asyncio
async def test_voucher_code_applies_on_top_of_brand_and_category_discounts():
    service = DiscountService()

    result = await service.calculate_cart_discounts(
        cart_items=cart_items,
        customer=customer,
        voucher_code="SUPER69",
    )

    # 81000 paisa -> 69% off -> 25110
    assert result.final_price == 25110
    assert "Voucher SUPER69 (69% off)" in result.applied_discounts


@pytest.mark.asyncio
async def test_validate_discount_code_true_for_existing_applicable_voucher():
    service = DiscountService()

    assert await service.validate_discount_code("SUPER69", cart_items, customer) is True


@pytest.mark.asyncio
async def test_validate_discount_code_false_for_unknown_code():
    service = DiscountService()

    assert await service.validate_discount_code("DOESNOTEXIST", cart_items, customer) is False


@pytest.mark.asyncio
async def test_duplicate_matching_brand_rules_do_not_stack_only_best_applies():
    fake_db = _FakeDB(
        [
            DiscountRule(type=DiscountType.BRAND, percent=Decimal("40"), brand="PUMA"),
            DiscountRule(type=DiscountType.BRAND, percent=Decimal("15"), brand="PUMA"),
        ]
    )
    service = DiscountService(db=fake_db)

    result = await service.calculate_cart_discounts(cart_items=cart_items, customer=customer)

    # base_price 150000 -> only the better 40% rule applies -> 90000, not both stacked
    assert result.final_price == 90000
    assert result.applied_discounts == {"Min 40% off on PUMA": 60000}
