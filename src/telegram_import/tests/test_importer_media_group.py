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

    def test_resync_with_same_photos_preserves_manual_order_and_primary(self):
        """Повторна синхронізація того самого поста (напр. `--full` ресинк)
        з ТИМИ САМИМИ фото не повинна скидати ручне перевпорядкування чи
        вибір головного фото в адмінці — лише додавати справді НОВІ фото."""
        leader = import_telegram_message(
            channel_id=self.channel_id,
            message_id=910,
            caption=self.caption,
            photo_file_ids=[],
            media_group_id="",
            photo_files=[
                ("tg-910-a.jpg", b"photo-a-bytes"),
                ("tg-910-b.jpg", b"photo-b-bytes"),
            ],
        )
        product = Product.objects.get(pk=leader.product_id)
        images = list(product.images.order_by("sort_order"))
        self.assertEqual(len(images), 2)

        # Імітуємо ручне редагування в адмінці: інвертуємо порядок і
        # обираємо друге фото головним.
        images[0].sort_order, images[1].sort_order = images[1].sort_order, images[0].sort_order
        images[0].is_primary, images[1].is_primary = False, True
        images[0].save(update_fields=["sort_order", "is_primary"])
        images[1].save(update_fields=["sort_order", "is_primary"])
        manual_state = {
            img.pk: (img.sort_order, img.is_primary)
            for img in product.images.all()
        }

        # Повторний імпорт того самого поста (той самий caption і ФОТО).
        import_telegram_message(
            channel_id=self.channel_id,
            message_id=910,
            caption=self.caption,
            photo_file_ids=[],
            media_group_id="",
            photo_files=[
                ("tg-910-a.jpg", b"photo-a-bytes"),
                ("tg-910-b.jpg", b"photo-b-bytes"),
            ],
        )

        product.refresh_from_db()
        self.assertEqual(product.images.count(), 2)
        for img in product.images.all():
            self.assertEqual(
                (img.sort_order, img.is_primary), manual_state[img.pk]
            )

    def test_telethon_follower_photo_bytes_synced_after_product_exists(self):
        """Telethon-синхронізація передає вже завантажені байти через
        `photo_files` (а не `photo_file_ids`, як вебхук). Коли фото
        альбому приходить окремим прогоном ПІСЛЯ того, як лідер-пост уже
        створив товар, ці байти раніше просто губились."""
        leader = import_telegram_message(
            channel_id=self.channel_id,
            message_id=900,
            caption=self.caption,
            photo_file_ids=[],
            media_group_id="album-3",
            photo_files=[("tg-900.jpg", b"leader-photo-bytes")],
        )
        product = Product.objects.get(pk=leader.product_id)
        self.assertEqual(product.images.count(), 1)

        follower = import_telegram_message(
            channel_id=self.channel_id,
            message_id=901,
            caption="",
            photo_file_ids=[],
            media_group_id="album-3",
            photo_files=[("tg-901.jpg", b"follower-photo-bytes")],
        )
        follower.refresh_from_db()
        self.assertEqual(follower.product_id, product.pk)
        product.refresh_from_db()
        self.assertEqual(product.images.count(), 2)

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
