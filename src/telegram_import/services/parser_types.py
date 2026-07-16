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
    # Стара ціна («🏷️ 4510 (замість 8200)») — заповнюється лише коли в
    # тексті явно вказані ОБИДВІ суми, інакше None.
    compare_price: Decimal | None = None


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

    @property
    def compare_price(self) -> Decimal | None:
        """Стара ціна, прив'язана саме до варіанта з `base_price`."""
        base = self.base_price
        if base is None:
            return None
        for variant in self.variants:
            if variant.price == base and variant.compare_price and variant.compare_price > base:
                return variant.compare_price
        return None
