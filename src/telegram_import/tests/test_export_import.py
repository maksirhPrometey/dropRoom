import json
import tempfile
from decimal import Decimal
from pathlib import Path

from django.test import TestCase

from src.catalog.models import Brand, Category
from src.telegram_import.services.export_import import (
    flatten_export_text,
    import_telegram_export,
    load_export_posts,
)


SAMPLE_EXPORT = {
    "name": "Test Channel",
    "type": "public_channel",
    "id": 2876543210,
    "messages": [
        {
            "id": 101,
            "type": "message",
            "text": "Coach Straw Tote Bag\n\n🏷️ 6050",
            "photo": "photos/bag.jpg",
            "width": 900,
            "height": 1200,
        },
        {
            "id": 102,
            "type": "message",
            "text": "",
            "photo": "photos/chart.jpg",
            "width": 1320,
            "height": 307,
        },
        {
            "id": 103,
            "type": "service",
            "text": "ignored",
        },
    ],
}


class TelegramExportImportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Brand.objects.get_or_create(name="Coach", defaults={"slug": "coach"})
        Category.objects.get_or_create(slug="bags", defaults={"name": "Bags"})

    def test_flatten_export_text(self):
        text = flatten_export_text(
            ["Coach ", {"type": "bold", "text": "Bag"}, "\n🏷️ 6050"]
        )
        self.assertIn("Coach", text)
        self.assertIn("6050", text)

    def test_import_from_export_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            export_dir = Path(tmp)
            photos_dir = export_dir / "photos"
            photos_dir.mkdir()
            (photos_dir / "bag.jpg").write_bytes(b"fake-image")
            (photos_dir / "chart.jpg").write_bytes(b"fake-chart")
            (export_dir / "result.json").write_text(
                json.dumps(SAMPLE_EXPORT),
                encoding="utf-8",
            )

            posts = load_export_posts(export_dir)[1]
            self.assertEqual(len(posts), 1)
            self.assertEqual(posts[0].message_id, 101)

            stats = import_telegram_export(export_dir)
            self.assertEqual(stats.imported, 1)

            from src.catalog.models import Product

            product = Product.objects.get()
            self.assertEqual(product.name, "Coach Straw Tote Bag")
            self.assertEqual(product.base_price, Decimal("6050"))
