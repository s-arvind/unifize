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

    def __post_init__(self) -> None:
        if self.base_price < 0:
            raise ValueError(f"base_price must be >= 0, got {self.base_price}")
        if self.current_price < 0:
            raise ValueError(f"current_price must be >= 0, got {self.current_price}")
