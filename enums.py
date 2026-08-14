from enum import Enum


class BrandTier(Enum):
    PREMIUM = "premium"
    REGULAR = "regular"
    BUDGET = "budget"


class CustomerTier(Enum):
    NEW = "new"
    REGULAR = "regular"
    VIP = "vip"


class Category(Enum):
    T_SHIRTS = "T-shirts"
    JEANS = "Jeans"
    SHOES = "Shoes"
    JACKETS = "Jackets"
    DRESSES = "Dresses"
    ACCESSORIES = "Accessories"


class DiscountType(Enum):
    BRAND = "brand"
    CATEGORY = "category"
    VOUCHER = "voucher"
    BANK_OFFER = "bank_offer"
