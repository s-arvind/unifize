from decimal import Decimal

import pytest

from services.discount_service import DiscountService
from seed import seed

_seeded = seed()
cart_items = _seeded["cart_items"]
customer = _seeded["customer"]
payment_info = _seeded["payment_info"]


@pytest.mark.asyncio
async def test_multiple_discount_scenario_stacks_brand_category_and_bank_offer():
    service = DiscountService()

    result = await service.calculate_cart_discounts(
        cart_items=cart_items,
        customer=customer,
        payment_info=payment_info,
    )

    # base_price 1500 -> 40% off (PUMA) -> 900 -> 10% off (T-shirts) -> 810
    # -> 10% off (ICICI bank offer, cart-level) -> 729
    assert result.original_price == Decimal("1500.00")
    assert result.final_price == Decimal("729.00")

    assert result.applied_discounts["Min 40% off on PUMA"] == Decimal("600.00")
    assert result.applied_discounts["Extra 10% off on T-shirts"] == Decimal("90.00")
    assert result.applied_discounts["10% instant discount on ICICI cards"] == Decimal("81.00")


@pytest.mark.asyncio
async def test_calculate_without_payment_info_skips_bank_offer():
    service = DiscountService()

    result = await service.calculate_cart_discounts(cart_items=cart_items, customer=customer)

    assert result.final_price == Decimal("810.00")
    assert "10% instant discount on ICICI cards" not in result.applied_discounts


@pytest.mark.asyncio
async def test_voucher_code_applies_on_top_of_brand_and_category_discounts():
    service = DiscountService()

    result = await service.calculate_cart_discounts(
        cart_items=cart_items,
        customer=customer,
        voucher_code="SUPER69",
    )

    # 810 -> 69% off -> 251.10
    assert result.final_price == Decimal("251.10")
    assert "Voucher SUPER69 (69% off)" in result.applied_discounts


@pytest.mark.asyncio
async def test_validate_discount_code_true_for_existing_applicable_voucher():
    service = DiscountService()

    assert await service.validate_discount_code("SUPER69", cart_items, customer) is True


@pytest.mark.asyncio
async def test_validate_discount_code_false_for_unknown_code():
    service = DiscountService()

    assert await service.validate_discount_code("DOESNOTEXIST", cart_items, customer) is False
