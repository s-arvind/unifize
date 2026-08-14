from dataclasses import dataclass

from enums import BrandTier, Category


@dataclass
class Product:
    id: str
    brand: str
    brand_tier: BrandTier
    category: Category
    base_price: int  # paisa
    current_price: int  # paisa, after brand/category discount
