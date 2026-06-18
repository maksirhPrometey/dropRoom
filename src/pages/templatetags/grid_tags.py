from django import template

register = template.Library()


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
