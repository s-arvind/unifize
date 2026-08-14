from dataclasses import dataclass
from typing import Optional

from models.entity import Entity


@dataclass(kw_only=True)
class PaymentInfo(Entity):
    method: str  # CARD, UPI, etc
    bank_name: Optional[str]
    card_type: Optional[str]  # CREDIT, DEBIT
