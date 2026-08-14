from dataclasses import dataclass

from models.entity import Entity
from models.product import Product


@dataclass(kw_only=True)
class CartItem(Entity):
    product: Product
    quantity: int
    size: str
