from dataclasses import dataclass
from typing import Dict

from models.entity import Entity


@dataclass(kw_only=True)
class DiscountedPrice(Entity):
    original_price: int  # paisa
    final_price: int  # paisa
    applied_discounts: Dict[str, int]  # discount_name -> amount in paisa
    message: str
