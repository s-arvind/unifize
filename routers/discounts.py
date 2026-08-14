from fastapi import APIRouter

from schemas import (
    CalculateDiscountsRequest,
    DiscountedPriceResponse,
    ValidateDiscountCodeRequest,
    ValidateDiscountCodeResponse,
)
from services.discount_service import DiscountService

router = APIRouter(prefix="/discounts", tags=["discounts"])
_service = DiscountService()


@router.post("/calculate", response_model=DiscountedPriceResponse)
async def calculate_discounts(request: CalculateDiscountsRequest) -> DiscountedPriceResponse:
    result = await _service.calculate_cart_discounts(
        cart_items=[item.to_entity() for item in request.cart_items],
        customer=request.customer.to_entity(),
        payment_info=request.payment_info.to_entity() if request.payment_info else None,
        voucher_code=request.voucher_code,
    )
    return DiscountedPriceResponse.from_entity(result)


@router.post("/validate", response_model=ValidateDiscountCodeResponse)
async def validate_discount_code(request: ValidateDiscountCodeRequest) -> ValidateDiscountCodeResponse:
    valid = await _service.validate_discount_code(
        code=request.code,
        cart_items=[item.to_entity() for item in request.cart_items],
        customer=request.customer.to_entity(),
    )
    return ValidateDiscountCodeResponse(valid=valid)
