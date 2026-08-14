from fastapi import APIRouter

from discount_service import DiscountService
from schemas import (
    CalculateDiscountsRequest,
    DiscountedPriceResponse,
    ValidateDiscountCodeRequest,
    ValidateDiscountCodeResponse,
)

router = APIRouter(prefix="/discounts", tags=["discounts"])
_service = DiscountService()


@router.post("/calculate", response_model=DiscountedPriceResponse)
async def calculate_discounts(request: CalculateDiscountsRequest) -> DiscountedPriceResponse:
    result = await _service.calculate_cart_discounts(
        cart_items=[item.to_domain() for item in request.cart_items],
        customer=request.customer.to_domain(),
        payment_info=request.payment_info.to_domain() if request.payment_info else None,
        voucher_code=request.voucher_code,
    )
    return DiscountedPriceResponse.from_domain(result)


@router.post("/validate", response_model=ValidateDiscountCodeResponse)
async def validate_discount_code(request: ValidateDiscountCodeRequest) -> ValidateDiscountCodeResponse:
    valid = await _service.validate_discount_code(
        code=request.code,
        cart_items=[item.to_domain() for item in request.cart_items],
        customer=request.customer.to_domain(),
    )
    return ValidateDiscountCodeResponse(valid=valid)
