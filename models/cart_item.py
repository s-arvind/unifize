from dataclasses import dataclass

from models.product import Product


@dataclass
class CartItem:
    product: Product
    quantity: int
    size: str
