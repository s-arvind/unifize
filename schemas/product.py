from pydantic import BaseModel

from enums import BrandTier, Category
from models import Product


class ProductSchema(BaseModel):
    id: str
    brand: str
    brand_tier: BrandTier
    category: Category
    base_price: int  # paisa
    current_price: int  # paisa

    def to_entity(self) -> Product:
        return Product(**self.model_dump())
