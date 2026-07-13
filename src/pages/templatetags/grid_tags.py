from django import template

from src.catalog.product_grid import pick_grid_columns

register = template.Library()

CATALOG_DESKTOP_COLS = 4


def ideal_cols(count: int, max_cols: int = 3) -> int:
    """Рівні ряди в grid: N % cols == 0 (див. Prometey card_skill)."""
    n = max(1, int(count))
    max_cols = max(1, int(max_cols))
    if n <= max_cols:
        return n
    for c in range(max_cols, 1, -1):
        if n % c == 0:
            return c
    return max_cols


@register.filter(name="ideal_cols")
def ideal_cols_filter(count, max_cols: int = 3) -> int:
    try:
        return ideal_cols(count, max_cols)
    except (TypeError, ValueError):
        return 1


@register.simple_tag
def catalog_grid_cols(item_count, paginated=True) -> int:
    """Пагінований каталог — фіксовані 4 col (shop_design §19)."""
    try:
        count = int(item_count)
    except (TypeError, ValueError):
        count = 0
    if paginated in (False, "false", "0", 0):
        return pick_grid_columns(count)
    return CATALOG_DESKTOP_COLS
