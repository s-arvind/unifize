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


def _to_rupees(paisa: int) -> float:
    return round(paisa / 100, 2)


class DiscountedPriceResponse(BaseModel):
    id: str
    original_price: float
    final_price: float
    applied_discounts: Dict[str, float]
    message: str
    created_at: float

    @classmethod
    def from_entity(cls, discounted_price: DiscountedPrice) -> "DiscountedPriceResponse":
        return cls(
            id=discounted_price.id,
            original_price=_to_rupees(discounted_price.original_price),
            final_price=_to_rupees(discounted_price.final_price),
            applied_discounts={
                name: _to_rupees(amount) for name, amount in discounted_price.applied_discounts.items()
            },
            message=discounted_price.message,
            created_at=discounted_price.created_at,
        )


class ValidateDiscountCodeResponse(BaseModel):
    valid: bool
