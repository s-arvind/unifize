from pydantic import BaseModel

from models import CartItem
from schemas.product import ProductSchema


class CartItemSchema(BaseModel):
    product: ProductSchema
    quantity: int
    size: str

    def to_domain(self) -> CartItem:
        return CartItem(product=self.product.to_domain(), quantity=self.quantity, size=self.size)
