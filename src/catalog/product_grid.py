def pick_grid_columns(count: int) -> int:
    """Desktop: 5, 4 або 3 колонки з мінімум 3 у неповному ряді (product_grid_skill)."""
    if count <= 0:
        return 2
    if count <= 2:
        return 3

    for cols in (5, 4, 3):
        if count % cols == 0:
            return cols

    for cols in (4, 5, 3):
        if count % cols >= 3:
            return cols

    for cols in (3, 5, 4):
        if count % cols == 2:
            return cols

    return 3
