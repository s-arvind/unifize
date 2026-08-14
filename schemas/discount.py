from decimal import Decimal
from typing import Dict, List, Optional

from pydantic import BaseModel

from models import DiscountedPrice
from schemas.cart_item import CartItemSchema
from schemas.customer_profile import CustomerProfileSchema
from schemas.payment_info import PaymentInfoSchema


class CalculateDiscountsRequest(BaseModel):
    cart_items: List[CartItemSchema]
    customer: CustomerProfileSchema
    payment_info: Optional[PaymentInfoSchema] = None
    voucher_code: Optional[str] = None


class ValidateDiscountCodeRequest(BaseModel):
    code: str
    cart_items: List[CartItemSchema]
    customer: CustomerProfileSchema


class DiscountedPriceResponse(BaseModel):
    original_price: Decimal
    final_price: Decimal
    applied_discounts: Dict[str, Decimal]
    message: str

    @classmethod
    def from_domain(cls, discounted_price: DiscountedPrice) -> "DiscountedPriceResponse":
        return cls(
            original_price=discounted_price.original_price,
            final_price=discounted_price.final_price,
            applied_discounts=discounted_price.applied_discounts,
            message=discounted_price.message,
        )


class ValidateDiscountCodeResponse(BaseModel):
    valid: bool
