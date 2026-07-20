import hashlib
import io
import logging
from typing import BinaryIO

from PIL import Image, ImageChops

logger = logging.getLogger("src.telegram_import")

SIZE_CHART_WIDE_RATIO = 1.75
SIZE_CHART_COMPACT_RATIO = 1.55
SIZE_CHART_COMPACT_MAX_SIDE = 700
SIZE_CHART_WHITE_RATIO = 0.90
SPEC_DIAGRAM_MAX_RATIO = 1.2
SPEC_DIAGRAM_MAX_SIDE = 820
SPEC_DIAGRAM_WHITE_RATIO = 0.72
SPEC_DIAGRAM_SAMPLE_MAX_PIXELS = 250_000
PHONE_SCREENSHOT_MIN_RATIO = 1.85
PHONE_SCREENSHOT_MAX_WIDTH = 1350
PHONE_SCREENSHOT_TOP_RATIO = 0.045
PHONE_SCREENSHOT_BOTTOM_RATIO = 0.07
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


def is_likely_size_chart(
    width: int,
    height: int,
    *,
    white_ratio: float | None = None,
) -> bool:
    if width <= 0 or height <= 0:
        return False

    ratio = width / height
    min_side = min(width, height)

    if ratio >= SIZE_CHART_WIDE_RATIO:
        return True

    if ratio >= SIZE_CHART_COMPACT_RATIO and min_side <= SIZE_CHART_COMPACT_MAX_SIDE:
        if white_ratio is None or white_ratio >= SIZE_CHART_WHITE_RATIO:
            return True

    if ratio >= SPEC_DIAGRAM_MAX_RATIO and min_side < 900:
        return bool(white_ratio is not None and white_ratio >= 0.92)

    return False


def _region_is_ui_bar(region: Image.Image) -> bool:
    pixels = list(region.getdata())
    if not pixels:
        return False

    brightness = [sum(channel) / 3 for channel in pixels]
    total = len(brightness)
    average = sum(brightness) / total
    variance = sum((value - average) ** 2 for value in brightness) / total
    dark_ratio = sum(1 for value in brightness if value < 60) / total
    light_ratio = sum(1 for value in brightness if value > 200) / total
    mixed_icons = dark_ratio > 0.02 and light_ratio > 0.02

    if variance < 350:
        return True
    if variance < 1400 and mixed_icons:
        return True
    return False


def _has_screenshot_ui_bars(content: bytes) -> bool:
    try:
        with Image.open(io.BytesIO(content)) as image:
            rgb = image.convert("RGB")
            width, height = rgb.size
            top_height = max(1, int(height * PHONE_SCREENSHOT_TOP_RATIO))
            bottom_height = max(1, int(height * PHONE_SCREENSHOT_BOTTOM_RATIO))
            top = rgb.crop((0, 0, width, top_height))
            bottom = rgb.crop((0, height - bottom_height, width, height))
            return _region_is_ui_bar(top) or _region_is_ui_bar(bottom)
    except OSError:
        return False


def is_likely_phone_screenshot(
    width: int,
    height: int,
    *,
    content: bytes | None = None,
) -> bool:
    if width <= 0 or height <= 0:
        return False

    ratio = height / width
    if ratio < PHONE_SCREENSHOT_MIN_RATIO or width > PHONE_SCREENSHOT_MAX_WIDTH:
        return False

    if ratio >= 1.95:
        return True

    if content and _has_screenshot_ui_bars(content):
        return True

    return False


def is_likely_spec_diagram(
    width: int,
    height: int,
    *,
    white_ratio: float | None = None,
) -> bool:
    if width <= 0 or height <= 0:
        return False
    if is_likely_size_chart(width, height, white_ratio=white_ratio):
        return True
    if white_ratio is None:
        return False
    if white_ratio < SPEC_DIAGRAM_WHITE_RATIO:
        return False
    # Студійні фото товарів часто квадратні ~700² на білому тлі
    # (white ≈ 0.73–0.80). Не плутаємо їх із розмірними схемами /
    # діаграмами, які зазвичай ширші або майже повністю білі.
    ratio = width / height if height else 0
    if 0.85 <= ratio <= 1.18:
        return False
    max_side = max(width, height)
    min_side = min(width, height)
    if max_side <= SPEC_DIAGRAM_MAX_SIDE and white_ratio >= 0.88:
        return True
    if min_side <= 700 and white_ratio >= 0.8:
        return True
    return False


def photo_score(
    width: int,
    height: int,
    *,
    white_ratio: float | None = None,
    content: bytes | None = None,
) -> int:
    if width <= 0 or height <= 0:
        return 0
    if is_likely_spec_diagram(width, height, white_ratio=white_ratio):
        return -1000
    if is_likely_phone_screenshot(width, height, content=content):
        return -2000
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


def _deduplicate_indices_by_content(photos: list[tuple[str, bytes]]) -> list[int]:
    """
    Той самий пост товару часто ресинхронізується кілька разів (повторний
    допис із тим самим caption, повторний прихід медіа-групи тощо) — і
    щоразу «merge_existing» перечитує вже збережені фото поруч із новими.
    Без дедуплікації за вмістом однакові байти накопичуються знову й знову
    під новими випадковими іменами файлів. MD5 тут — лише швидкий і
    достатньо надійний спосіб виявити побайтово ідентичні копії, а не
    криптографічний захист. Повертає індекси, які треба лишити (щоб
    паралельний список `sizes` можна було відфільтрувати так само).
    """
    seen: set[str] = set()
    keep: list[int] = []
    for index, (_filename, content) in enumerate(photos):
        digest = hashlib.md5(content).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        keep.append(index)
    return keep


def rank_photo_files(
    photos: list[tuple[str, bytes]],
    *,
    sizes: list[tuple[int, int]] | None = None,
) -> list[tuple[str, bytes]]:
    if not photos:
        return []

    keep_indices = _deduplicate_indices_by_content(photos)
    if len(keep_indices) != len(photos):
        photos = [photos[i] for i in keep_indices]
        if sizes:
            sizes = [sizes[i] for i in keep_indices if i < len(sizes)]

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
            (
                photo_score(width, height, white_ratio=ratio, content=content),
                filename,
                content,
            )
        )

    ranked.sort(key=lambda item: item[0], reverse=True)
    product_photos = [
        (filename, content) for score, filename, content in ranked if score > -500
    ]
    if product_photos:
        return product_photos

    viable = [(score, filename, content) for score, filename, content in ranked if score > -900]
    if viable:
        _score, filename, content = max(viable, key=lambda item: len(item[2]))
        return [(filename, content)]

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
