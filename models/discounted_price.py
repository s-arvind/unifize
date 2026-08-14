from dataclasses import dataclass
from decimal import Decimal
from typing import Dict

from models.entity import Entity


@dataclass(kw_only=True)
class DiscountedPrice(Entity):
    original_price: Decimal
    final_price: Decimal
    applied_discounts: Dict[str, Decimal]  # discount_name -> amount
    message: str
