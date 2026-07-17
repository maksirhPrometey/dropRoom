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
from src.telegram_import.services.caption_selection import merge_message_captions


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

    def test_album_with_stock_note_stays_single_product(self):
        export = {
            "name": "Test Channel",
            "type": "public_channel",
            "id": 2876543210,
            "messages": [
                {
                    "id": 113463,
                    "type": "message",
                    "date_unixtime": "1783683316",
                    "text": "👜 Сумка-шопер Lacoste L.12.12\n\n🏷️3450",
                    "photo": "photos/lacoste-main.jpg",
                    "width": 800,
                    "height": 1091,
                },
                {
                    "id": 113464,
                    "type": "message",
                    "date_unixtime": "1783683316",
                    "text": "коричневий в наявності один",
                    "photo": "photos/lacoste-brown.jpg",
                    "width": 800,
                    "height": 1091,
                },
                {
                    "id": 113465,
                    "type": "message",
                    "date_unixtime": "1783683316",
                    "text": "",
                    "photo": "photos/lacoste-extra.jpg",
                    "width": 1773,
                    "height": 2560,
                },
            ],
        }

        with tempfile.TemporaryDirectory() as tmp:
            export_dir = Path(tmp)
            photos_dir = export_dir / "photos"
            photos_dir.mkdir()
            for name in ("lacoste-main.jpg", "lacoste-brown.jpg", "lacoste-extra.jpg"):
                (photos_dir / name).write_bytes(f"fake-image-{name}".encode())

            (export_dir / "result.json").write_text(
                json.dumps(export),
                encoding="utf-8",
            )

            posts = load_export_posts(export_dir)[1]
            self.assertEqual(len(posts), 1)
            self.assertEqual(posts[0].message_id, 113463)
            self.assertIn("Lacoste", posts[0].caption)
            self.assertIn("коричневий в наявності один", posts[0].caption)
            self.assertEqual(len(posts[0].photo_files), 3)

    def test_merge_message_captions_prefers_product_description(self):
        merged = merge_message_captions(
            [
                "коричневий в наявності один",
                "👜 Сумка-шопер Lacoste L.12.12\n\n🏷️3450",
            ]
        )
        self.assertTrue(merged.startswith("👜"))
        self.assertIn("коричневий в наявності один", merged)

    def test_same_timestamp_different_captions_stay_separate(self):
        """Bulk-forward: кілька товарів в одну секунду не зливаються."""
        export = {
            "name": "DropGoods",
            "type": "private_group",
            "id": 5540595444,
            "messages": [
                {
                    "id": 1,
                    "type": "message",
                    "date_unixtime": "1784094712",
                    "text": "Adidas One\n\nУ наявності: 37\n🏷️8200",
                    "photo": "photos/a1.jpg",
                    "width": 800,
                    "height": 1000,
                },
                {
                    "id": 2,
                    "type": "message",
                    "date_unixtime": "1784094712",
                    "text": "",
                    "photo": "photos/a2.jpg",
                    "width": 800,
                    "height": 1000,
                },
                {
                    "id": 3,
                    "type": "message",
                    "date_unixtime": "1784094712",
                    "text": "Nike Two\n\n39 — 5490 грн\n40 — 5690 грн",
                    "photo": "photos/n1.jpg",
                    "width": 800,
                    "height": 1000,
                },
                {
                    "id": 4,
                    "type": "message",
                    "date_unixtime": "1784094712",
                    "text": "",
                    "photo": "photos/n2.jpg",
                    "width": 800,
                    "height": 1000,
                },
            ],
        }

        with tempfile.TemporaryDirectory() as tmp:
            export_dir = Path(tmp)
            photos_dir = export_dir / "photos"
            photos_dir.mkdir()
            for name in ("a1.jpg", "a2.jpg", "n1.jpg", "n2.jpg"):
                (photos_dir / name).write_bytes(f"fake-image-{name}".encode())
            (export_dir / "result.json").write_text(
                json.dumps(export),
                encoding="utf-8",
            )

            posts = load_export_posts(export_dir)[1]
            self.assertEqual(len(posts), 2)
            self.assertIn("Adidas", posts[0].caption)
            self.assertEqual(len(posts[0].photo_files), 2)
            self.assertIn("Nike", posts[1].caption)
            self.assertEqual(len(posts[1].photo_files), 2)
