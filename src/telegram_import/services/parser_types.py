from dataclasses import dataclass, field
from decimal import Decimal

from src.catalog.models import Brand, Category


@dataclass
class ParsedVariant:
    size: str
    price: Decimal
    stock_qty: int = 0
    is_available: bool = True
    color: str | None = None
    note: str = ""


@dataclass
class ParsedProduct:
    name: str
    description: str
    brand: Brand | None
    category: Category | None
    gender: str
    variants: list[ParsedVariant] = field(default_factory=list)

    @property
    def base_price(self) -> Decimal | None:
        if not self.variants:
            return None
        available = [
            v.price
            for v in self.variants
            if v.is_available and v.price is not None and v.price > 0
        ]
        if available:
            return min(available)
        priced = [
            v.price for v in self.variants if v.price is not None and v.price > 0
        ]
        return min(priced) if priced else None
