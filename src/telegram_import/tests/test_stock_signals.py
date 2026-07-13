from django.test import SimpleTestCase

from src.telegram_import.services.stock_signals import (
    caption_signals_in_stock,
    line_signals_in_stock,
)

COACH_BAG = """Coach Straw Tote Bag ❤️🤍

Стильна літня сумка.

🏷️ 6050"""

POLO_CAP = """В наявності кепка Polo

one size

🏷️999"""


class StockSignalTests(SimpleTestCase):
    def test_coach_bag_is_preorder_only(self):
        self.assertFalse(caption_signals_in_stock(COACH_BAG))

    def test_polo_cap_signals_in_stock(self):
        self.assertTrue(caption_signals_in_stock(POLO_CAP))

    def test_line_with_pairs_in_stock(self):
        line = "• 38 — 23,5 см — 🏷️ 1820 грн ( 1 пара є в наявності )"
        self.assertTrue(line_signals_in_stock(line))
