from decimal import Decimal

import pytest

from enums import BrandTier, Category, CustomerTier, DiscountType
from models import CartItem, CustomerProfile, DiscountRule, PaymentInfo, Product
from services.discount_service import DiscountService, _best_match, _percent_of
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


def _product(**overrides) -> Product:
    defaults = dict(
        id="prod-x",
        brand="PUMA",
        brand_tier=BrandTier.PREMIUM,
        category=Category.T_SHIRTS,
        base_price=150000,
        current_price=150000,
    )
    defaults.update(overrides)
    return Product(**defaults)


def _item(**overrides) -> CartItem:
    product = overrides.pop("product", None) or _product()
    return CartItem(product=product, quantity=overrides.pop("quantity", 1), size=overrides.pop("size", "M"))


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
async def test_voucher_code_lookup_is_case_insensitive():
    service = DiscountService()

    result = await service.calculate_cart_discounts(
        cart_items=cart_items,
        customer=customer,
        voucher_code="super69",
    )

    assert result.final_price == 25110


@pytest.mark.asyncio
async def test_calculate_with_unknown_voucher_code_skips_it_with_message():
    service = DiscountService()

    result = await service.calculate_cart_discounts(
        cart_items=cart_items,
        customer=customer,
        voucher_code="DOESNOTEXIST",
    )

    # brand+category still apply, voucher just doesn't
    assert result.final_price == 81000
    assert "Voucher DOESNOTEXIST does not exist" in result.message


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


def test_best_match_picks_highest_percent_and_none_when_nothing_matches():
    rules = [
        DiscountRule(type=DiscountType.CATEGORY, percent=Decimal("10"), category=Category.T_SHIRTS),
        DiscountRule(type=DiscountType.CATEGORY, percent=Decimal("25"), category=Category.T_SHIRTS),
    ]

    best = _best_match(rules, lambda rule: True)
    assert best.percent == Decimal("25")

    assert _best_match(rules, lambda rule: False) is None


@pytest.mark.asyncio
async def test_discount_rule_rejects_percent_out_of_range():
    with pytest.raises(ValueError):
        DiscountRule(type=DiscountType.BRAND, percent=Decimal("150"), brand="PUMA")
    with pytest.raises(ValueError):
        DiscountRule(type=DiscountType.BRAND, percent=Decimal("0"), brand="PUMA")


@pytest.mark.asyncio
async def test_discount_rule_rejects_missing_type_specific_field():
    with pytest.raises(ValueError):
        DiscountRule(type=DiscountType.BRAND, percent=Decimal("40"))  # no brand
    with pytest.raises(ValueError):
        DiscountRule(type=DiscountType.CATEGORY, percent=Decimal("10"))  # no category
    with pytest.raises(ValueError):
        DiscountRule(type=DiscountType.VOUCHER, percent=Decimal("50"))  # no code
    with pytest.raises(ValueError):
        DiscountRule(type=DiscountType.BANK_OFFER, percent=Decimal("10"))  # no bank_name


@pytest.mark.asyncio
async def test_product_rejects_negative_prices():
    with pytest.raises(ValueError):
        _product(base_price=-100)
    with pytest.raises(ValueError):
        _product(current_price=-100)


@pytest.mark.asyncio
async def test_cart_item_rejects_non_positive_quantity():
    with pytest.raises(ValueError):
        _item(quantity=0)
    with pytest.raises(ValueError):
        _item(quantity=-1)


@pytest.mark.asyncio
async def test_voucher_brand_exclusion_makes_it_ineligible():
    fake_db = _FakeDB(
        [DiscountRule(type=DiscountType.VOUCHER, percent=Decimal("50"), code="NOPUMA", excluded_brands=["PUMA"])]
    )
    service = DiscountService(db=fake_db)

    valid = await service.validate_discount_code("NOPUMA", [_item()], customer)
    result = await service.calculate_cart_discounts(cart_items=[_item()], customer=customer, voucher_code="NOPUMA")

    assert valid is False
    assert result.final_price == 150000
    assert "Voucher NOPUMA does not apply to any item in the cart" in result.message


@pytest.mark.asyncio
async def test_voucher_category_restriction():
    fake_db = _FakeDB(
        [
            DiscountRule(
                type=DiscountType.VOUCHER, percent=Decimal("50"), code="JEANSONLY",
                allowed_categories=[Category.JEANS],
            ),
            DiscountRule(
                type=DiscountType.VOUCHER, percent=Decimal("50"), code="TSHIRTSONLY",
                allowed_categories=[Category.T_SHIRTS],
            ),
        ]
    )
    service = DiscountService(db=fake_db)

    assert await service.validate_discount_code("JEANSONLY", [_item()], customer) is False
    assert await service.validate_discount_code("TSHIRTSONLY", [_item()], customer) is True


@pytest.mark.asyncio
async def test_voucher_min_tier_requirement():
    fake_db = _FakeDB(
        [DiscountRule(type=DiscountType.VOUCHER, percent=Decimal("50"), code="VIPONLY", min_tier=CustomerTier.VIP)]
    )
    service = DiscountService(db=fake_db)
    regular_customer = CustomerProfile(id="cust-reg", tier=CustomerTier.REGULAR)
    vip_customer = CustomerProfile(id="cust-vip", tier=CustomerTier.VIP)

    assert await service.validate_discount_code("VIPONLY", [_item()], regular_customer) is False
    assert await service.validate_discount_code("VIPONLY", [_item()], vip_customer) is True


@pytest.mark.asyncio
async def test_quantity_greater_than_one_multiplies_line_price():
    fake_db = _FakeDB([DiscountRule(type=DiscountType.BRAND, percent=Decimal("40"), brand="PUMA")])
    service = DiscountService(db=fake_db)
    item = _item(quantity=3)  # 150000 * 3 = 450000

    result = await service.calculate_cart_discounts(cart_items=[item], customer=customer)

    assert result.original_price == 450000
    assert result.applied_discounts["Min 40% off on PUMA"] == 180000
    assert result.final_price == 270000


@pytest.mark.asyncio
async def test_multiple_cart_items_aggregate_original_price_and_discounts():
    fake_db = _FakeDB([DiscountRule(type=DiscountType.BRAND, percent=Decimal("40"), brand="PUMA")])
    service = DiscountService(db=fake_db)
    items = [_item(product=_product(id="p1")), _item(product=_product(id="p2"))]

    result = await service.calculate_cart_discounts(cart_items=items, customer=customer)

    assert result.original_price == 300000  # two items, 150000 each
    assert result.applied_discounts["Min 40% off on PUMA"] == 120000  # 60000 summed across both items
    assert result.final_price == 180000


@pytest.mark.asyncio
async def test_empty_cart_returns_zero_price_and_no_discounts():
    service = DiscountService()

    result = await service.calculate_cart_discounts(cart_items=[], customer=customer)

    assert result.original_price == 0
    assert result.final_price == 0
    assert result.applied_discounts == {}
    assert result.message == "No discounts applied"


@pytest.mark.asyncio
async def test_item_with_no_matching_rules_gets_no_discount():
    fake_db = _FakeDB([DiscountRule(type=DiscountType.BRAND, percent=Decimal("40"), brand="PUMA")])
    service = DiscountService(db=fake_db)
    nike_item = _item(product=_product(id="p-nike", brand="NIKE", category=Category.SHOES))

    result = await service.calculate_cart_discounts(cart_items=[nike_item], customer=customer)

    assert result.applied_discounts == {}
    assert result.final_price == 150000
    assert result.message == "No discounts applied"


@pytest.mark.asyncio
async def test_unmatched_bank_name_skips_bank_offer():
    fake_db = _FakeDB([DiscountRule(type=DiscountType.BANK_OFFER, percent=Decimal("10"), bank_name="ICICI")])
    service = DiscountService(db=fake_db)
    other_bank = PaymentInfo(method="CARD", bank_name="HDFC", card_type="CREDIT")

    result = await service.calculate_cart_discounts(cart_items=[_item()], customer=customer, payment_info=other_bank)

    assert result.applied_discounts == {}
    assert result.final_price == 150000


def test_percent_of_rounds_half_up_on_fractional_paisa():
    assert _percent_of(3, Decimal("50")) == 2  # 1.5 -> 2
    assert _percent_of(5, Decimal("10")) == 1  # 0.5 -> 1
    assert _percent_of(100, Decimal("33.5")) == 34  # 33.5 -> 34
