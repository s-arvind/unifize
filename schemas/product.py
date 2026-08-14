from decimal import Decimal

from pydantic import BaseModel

from enums import BrandTier
from models import Product


class ProductSchema(BaseModel):
    id: str
    brand: str
    brand_tier: BrandTier
    category: str
    base_price: Decimal
    current_price: Decimal

    def to_entity(self) -> Product:
        return Product(**self.model_dump())
