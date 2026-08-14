from typing import Optional

from pydantic import BaseModel

from models import PaymentInfo


class PaymentInfoSchema(BaseModel):
    method: str
    bank_name: Optional[str] = None
    card_type: Optional[str] = None

    def to_entity(self) -> PaymentInfo:
        return PaymentInfo(**self.model_dump())
