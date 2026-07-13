IN_STOCK_LEAD_DAYS = 3
PREORDER_LEAD_DAYS = 14


def fulfillment_status_label(*, in_stock: bool) -> str:
    if in_stock:
        return "В наявності"
    return "Під замовлення"


def fulfillment_eta_label(*, in_stock: bool) -> str:
    if in_stock:
        return f"Орієнтовно {IN_STOCK_LEAD_DAYS} робочі дні"
    return f"Орієнтовно {PREORDER_LEAD_DAYS} днів"
