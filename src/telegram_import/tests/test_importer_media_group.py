from io import BytesIO
from unittest.mock import patch

from django.test import TestCase

from src.catalog.models import Brand, Category, Product
from src.telegram_import.models import TelegramImport
from src.telegram_import.services.importer import import_telegram_message
from src.telegram_import.services.telegram_api import TelegramPhoto


def _fake_photo(file_id: str) -> TelegramPhoto:
    return TelegramPhoto(
        file_id=file_id,
        content=b"fake-jpeg",
        filename=f"{file_id}.jpg",
    )


class MediaGroupImportTests(TestCase):
    def setUp(self):
        self.brand, _ = Brand.objects.get_or_create(
            name="Tommy Hilfiger",
            defaults={"slug": "tommy-hilfiger"},
        )
        self.category, _ = Category.objects.get_or_create(
            name="Knitwear",
            defaults={"slug": "knitwear"},
        )
        self.channel_id = -5566899151
        self.caption = (
            "Tommy Jeans Cardigan\n\n"
            "Елегантний кардиган Tommy Jeans.\n\n"
            "S — груди 88-92 см\n"
            "M — груди 92-96 см\n"
            "L — груди 96-100 см\n\n"
            "під замовлення 🏷️2999"
        )

    @patch("src.telegram_import.services.importer.download_photo")
    def test_media_group_collects_all_photos(self, download_photo_mock):
        download_photo_mock.side_effect = lambda file_id: _fake_photo(file_id)

        import_telegram_message(
            channel_id=self.channel_id,
            message_id=501,
            caption="",
            photo_file_ids=["photo-b"],
            media_group_id="album-1",
        )
        leader = import_telegram_message(
            channel_id=self.channel_id,
            message_id=500,
            caption=self.caption,
            photo_file_ids=["photo-a"],
            media_group_id="album-1",
        )
        import_telegram_message(
            channel_id=self.channel_id,
            message_id=502,
            caption="",
            photo_file_ids=["photo-c"],
            media_group_id="album-1",
        )

        product = Product.objects.get(pk=leader.product_id)
        self.assertEqual(product.name, "Tommy Jeans Cardigan")
        self.assertEqual(product.images.count(), 3)
        self.assertEqual(
            TelegramImport.objects.filter(product=product).count(),
            3,
        )

    @patch("src.telegram_import.services.importer.download_photo")
    def test_follower_before_leader_waits_without_product(self, download_photo_mock):
        download_photo_mock.side_effect = lambda file_id: _fake_photo(file_id)

        follower = import_telegram_message(
            channel_id=self.channel_id,
            message_id=601,
            caption="",
            photo_file_ids=["photo-b"],
            media_group_id="album-2",
        )
        self.assertEqual(follower.status, TelegramImport.STATUS_PENDING)
        self.assertIsNone(follower.product_id)
        self.assertEqual(Product.objects.count(), 0)

        leader = import_telegram_message(
            channel_id=self.channel_id,
            message_id=600,
            caption=self.caption,
            photo_file_ids=["photo-a"],
            media_group_id="album-2",
        )

        follower.refresh_from_db()
        product = Product.objects.get(pk=leader.product_id)
        self.assertEqual(follower.product_id, product.pk)
        self.assertEqual(product.images.count(), 2)

    def test_photo_without_caption_is_skipped(self):
        record = import_telegram_message(
            channel_id=self.channel_id,
            message_id=700,
            caption="",
            photo_file_ids=["photo-x"],
            media_group_id="",
        )
        self.assertEqual(record.status, TelegramImport.STATUS_SKIPPED)
        self.assertEqual(record.error, "Фото без опису")
        self.assertEqual(Product.objects.count(), 0)

    @patch("src.telegram_import.services.importer.download_photo")
    def test_unmatched_brand_fails_without_env_default(self, download_photo_mock):
        download_photo_mock.side_effect = lambda file_id: _fake_photo(file_id)
        from src.telegram_import.services.importer import ImportError as TGImportError

        with self.settings(
            TELEGRAM_DEFAULT_BRAND_ID=0,
            TELEGRAM_DEFAULT_CATEGORY_ID=0,
        ):
            with self.assertRaises(TGImportError) as ctx:
                import_telegram_message(
                    channel_id=self.channel_id,
                    message_id=800,
                    caption="Невідома річ XYZ\n\n🏷️2500",
                    photo_file_ids=["photo-u"],
                )
        self.assertIn("бренд", str(ctx.exception).lower())
        self.assertEqual(Product.objects.count(), 0)
