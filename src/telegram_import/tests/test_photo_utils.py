from io import BytesIO
from pathlib import Path

from django.test import TestCase
from PIL import Image

from src.telegram_import.services.photo_utils import (
    is_likely_phone_screenshot,
    is_likely_size_chart,
    is_likely_spec_diagram,
    normalize_product_image,
    rank_photo_files,
)


def _jpeg_bytes(width: int, height: int, color: str = "red") -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (width, height), color).save(buffer, format="JPEG")
    return buffer.getvalue()


class PhotoRankingTests(TestCase):
    def test_size_chart_detected(self):
        self.assertTrue(is_likely_size_chart(1320, 666))
        self.assertTrue(is_likely_size_chart(1320, 666, white_ratio=0.93))
        self.assertFalse(is_likely_size_chart(1114, 742, white_ratio=0.81))
        self.assertFalse(is_likely_size_chart(1200, 800, white_ratio=0.87))

    def test_landscape_product_photo_kept(self):
        product = ("product.jpg", _jpeg_bytes(1200, 800))
        ranked = rank_photo_files([product], sizes=[(1200, 800)])
        self.assertEqual(ranked[0][0], "product.jpg")
        self.assertEqual(len(ranked), 1)

    def test_size_chart_only_returns_empty(self):
        chart = ("chart.jpg", _jpeg_bytes(1320, 666))
        self.assertEqual(rank_photo_files([chart], sizes=[(1320, 666)]), [])

    def test_product_photo_preferred(self):
        chart = ("chart.jpg", _jpeg_bytes(1320, 666))
        product = ("product.jpg", _jpeg_bytes(1008, 1280))
        ranked = rank_photo_files([chart, product])
        self.assertEqual(ranked[0][0], "product.jpg")
        self.assertEqual(len(ranked), 1)

    def test_spec_diagram_filtered(self):
        diagram = ("diagram.jpg", _jpeg_bytes(520, 650, "white"))
        product = ("product.jpg", _jpeg_bytes(1008, 1280, "red"))
        ranked = rank_photo_files([diagram, product])
        self.assertEqual(ranked[0][0], "product.jpg")
        self.assertEqual(len(ranked), 1)

    def test_spec_diagram_detected_by_white_ratio(self):
        self.assertTrue(
            is_likely_spec_diagram(520, 650, white_ratio=0.82),
        )
        self.assertFalse(
            is_likely_spec_diagram(1024, 1280, white_ratio=0.62),
        )

    def test_normalize_trims_white_borders(self):
        buffer = BytesIO()
        image = Image.new("RGB", (400, 500), "white")
        for x in range(120, 280):
            for y in range(150, 350):
                image.putpixel((x, y), (180, 40, 40))
        image.save(buffer, format="JPEG")
        normalized = normalize_product_image(buffer.getvalue())
        with Image.open(BytesIO(normalized)) as result:
            self.assertLess(result.size[0], 400)
            self.assertLess(result.size[1], 500)

    def test_phone_screenshot_filtered(self):
        screenshot = ("screenshot.jpg", _jpeg_bytes(1178, 2560, "white"))
        product = ("product.jpg", _jpeg_bytes(1920, 2560, "red"))
        ranked = rank_photo_files(
            [screenshot, product],
            sizes=[(1178, 2560), (1920, 2560)],
        )
        self.assertEqual(ranked[0][0], "product.jpg")
        self.assertEqual(len(ranked), 1)

    def test_phone_screenshot_detected_with_real_seed_photo(self):
        photo_path = (
            Path(__file__).resolve().parents[3]
            / "seed_data"
            / "photos"
            / "photo_161@10-07-2026_14-20-07.jpg"
        )
        if not photo_path.is_file():
            self.skipTest("seed screenshot sample is missing")

        content = photo_path.read_bytes()
        self.assertTrue(is_likely_phone_screenshot(1178, 2560, content=content))
        self.assertEqual(
            rank_photo_files([("screenshot.jpg", content)], sizes=[(1178, 2560)]),
            [],
        )
