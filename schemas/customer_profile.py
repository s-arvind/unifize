from pydantic import BaseModel

from enums import CustomerTier
from models import CustomerProfile


class CustomerProfileSchema(BaseModel):
    id: str
    tier: CustomerTier

    def to_domain(self) -> CustomerProfile:
        return CustomerProfile(**self.model_dump())
