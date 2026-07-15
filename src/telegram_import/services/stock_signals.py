import re

_IN_STOCK_SIGNAL_RE = re.compile(
    r"(?:"
    r"в\s+наявності|"
    r"у\s+наявності|"
    r"наявності\s*\d+|"
    r"\d+\s*пар[аи]?\s*(?:є\s*)?в\s*наявності|"
    r"\d+\s*шт\.?\s*на\s*склад|"
    r"(?:\d+\s*)?є\s*в\s*наявності|"
    r"лише\s+\d+\s+в\s+наявності|"
    r"в\s+наявності\s+\d+|"
    r"\(\s*\d+\s*шт\.?\s*\)"
    r")",
    re.IGNORECASE,
)


def caption_signals_in_stock(caption: str) -> bool:
    return bool(_IN_STOCK_SIGNAL_RE.search(caption))


def line_signals_in_stock(line: str) -> bool:
    return bool(_IN_STOCK_SIGNAL_RE.search(line))
