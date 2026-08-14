from dataclasses import dataclass

from models.entity import Entity
from models.product import Product


@dataclass(kw_only=True)
class CartItem(Entity):
    product: Product
    quantity: int
    size: str

    def __post_init__(self) -> None:
        if self.quantity < 1:
            raise ValueError(f"quantity must be >= 1, got {self.quantity}")
