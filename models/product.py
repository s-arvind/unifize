from dataclasses import dataclass
from decimal import Decimal

from enums import BrandTier


@dataclass
class Product:
    id: str
    brand: str
    brand_tier: BrandTier
    category: str
    base_price: Decimal
    current_price: Decimal  # After brand/category discount
