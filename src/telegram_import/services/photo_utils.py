import io
import logging
from typing import BinaryIO

from PIL import Image, ImageChops

logger = logging.getLogger("src.telegram_import")

SIZE_CHART_MAX_RATIO = 1.35
SPEC_DIAGRAM_MAX_RATIO = 1.2
SPEC_DIAGRAM_MAX_SIDE = 820
SPEC_DIAGRAM_WHITE_RATIO = 0.72
SPEC_DIAGRAM_SAMPLE_MAX_PIXELS = 250_000
TRIM_PADDING_PX = 16
TRIM_MIN_CONTENT_RATIO = 0.38


def _image_size(data: bytes) -> tuple[int, int]:
    with Image.open(io.BytesIO(data)) as image:
        return image.size


def _white_ratio(data: bytes) -> float | None:
    try:
        with Image.open(io.BytesIO(data)) as image:
            rgb = image.convert("RGB")
            width, height = rgb.size
            pixels = width * height
            if pixels > SPEC_DIAGRAM_SAMPLE_MAX_PIXELS:
                scale = (SPEC_DIAGRAM_SAMPLE_MAX_PIXELS / pixels) ** 0.5
                rgb = rgb.resize(
                    (max(1, int(width * scale)), max(1, int(height * scale))),
                    Image.Resampling.BILINEAR,
                )
            pixels = list(rgb.getdata())
            total = len(pixels)
            if total == 0:
                return None
            white = sum(
                1 for r, g, b in pixels if r > 240 and g > 240 and b > 240
            )
            return white / total
    except OSError:
        return None


def is_likely_size_chart(width: int, height: int) -> bool:
    if width <= 0 or height <= 0:
        return False
    ratio = width / height
    if ratio >= SIZE_CHART_MAX_RATIO:
        return True
    return ratio >= SPEC_DIAGRAM_MAX_RATIO and min(width, height) < 900


def is_likely_spec_diagram(
    width: int,
    height: int,
    *,
    white_ratio: float | None = None,
) -> bool:
    if width <= 0 or height <= 0:
        return False
    if is_likely_size_chart(width, height):
        return True
    if white_ratio is None:
        return False
    if white_ratio < SPEC_DIAGRAM_WHITE_RATIO:
        return False
    max_side = max(width, height)
    min_side = min(width, height)
    if max_side <= SPEC_DIAGRAM_MAX_SIDE:
        return True
    if min_side <= 700 and white_ratio >= 0.8:
        return True
    return False


def photo_score(
    width: int,
    height: int,
    *,
    white_ratio: float | None = None,
) -> int:
    if width <= 0 or height <= 0:
        return 0
    if is_likely_spec_diagram(width, height, white_ratio=white_ratio):
        return -1000
    ratio = width / height
    score = height
    if height >= width:
        score += 200
    if 0.65 <= ratio <= 1.1:
        score += 100
    if white_ratio is not None and white_ratio > 0.85:
        score -= 80
    if max(width, height) < 900:
        score -= 40
    return score


def rank_photo_files(
    photos: list[tuple[str, bytes]],
    *,
    sizes: list[tuple[int, int]] | None = None,
) -> list[tuple[str, bytes]]:
    if not photos:
        return []

    ranked: list[tuple[int, str, bytes]] = []
    for index, (filename, content) in enumerate(photos):
        if sizes and index < len(sizes) and sizes[index][0] and sizes[index][1]:
            width, height = sizes[index]
        else:
            try:
                width, height = _image_size(content)
            except OSError:
                logger.warning("Не вдалося прочитати розмір зображення %s", filename)
                width, height = 0, 0

        ratio = _white_ratio(content)
        ranked.append(
            (photo_score(width, height, white_ratio=ratio), filename, content)
        )

    ranked.sort(key=lambda item: item[0], reverse=True)
    product_photos = [
        (filename, content) for score, filename, content in ranked if score > -500
    ]
    if product_photos:
        return product_photos
    return []


def normalize_product_image(content: bytes) -> bytes:
    """Обрізає білі поля навколо товару на студійному фото."""
    try:
        with Image.open(io.BytesIO(content)) as image:
            rgb = image.convert("RGB")
            width, height = rgb.size
            background = Image.new("RGB", rgb.size, (255, 255, 255))
            diff = ImageChops.difference(rgb, background)
            bbox = diff.getbbox()
            if not bbox:
                return content

            left, top, right, bottom = bbox
            content_width = right - left
            content_height = bottom - top
            if (
                content_width < width * TRIM_MIN_CONTENT_RATIO
                or content_height < height * TRIM_MIN_CONTENT_RATIO
            ):
                return content

            left = max(0, left - TRIM_PADDING_PX)
            top = max(0, top - TRIM_PADDING_PX)
            right = min(width, right + TRIM_PADDING_PX)
            bottom = min(height, bottom + TRIM_PADDING_PX)
            if left == 0 and top == 0 and right == width and bottom == height:
                return content

            cropped = rgb.crop((left, top, right, bottom))
            buffer = io.BytesIO()
            cropped.save(buffer, format="JPEG", quality=92, optimize=True)
            return buffer.getvalue()
    except OSError:
        logger.warning("Не вдалося нормалізувати зображення")
        return content
