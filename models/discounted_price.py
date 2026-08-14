from dataclasses import dataclass
from decimal import Decimal
from typing import Dict


@dataclass
class DiscountedPrice:
    original_price: Decimal
    final_price: Decimal
    applied_discounts: Dict[str, Decimal]  # discount_name -> amount
    message: str
