from enum import Enum


class BrandTier(Enum):
    PREMIUM = "premium"
    REGULAR = "regular"
    BUDGET = "budget"


class CustomerTier(Enum):
    NEW = "new"
    REGULAR = "regular"
    VIP = "vip"
