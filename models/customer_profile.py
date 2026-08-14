from dataclasses import dataclass

from enums import CustomerTier


@dataclass
class CustomerProfile:
    id: str
    tier: CustomerTier
