import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from src.telegram_import.models import TelegramSyncState
from src.telegram_import.services.caption_selection import merge_message_captions
from src.telegram_import.services.importer import ImportError, import_telegram_message
from src.telegram_import.services.photo_utils import rank_photo_files

logger = logging.getLogger("src.telegram_import")


@dataclass
class ExportStats:
    processed: int = 0
    imported: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class ExportPost:
    message_id: int
    caption: str
    media_group_id: str
    photo_files: list[tuple[str, bytes]]


def flatten_export_text(text) -> str:
    if isinstance(text, str):
        return text.strip()
    if not isinstance(text, list):
        return ""
    parts: list[str] = []
    for item in text:
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, dict):
            parts.append(str(item.get("text", "")))
    return "".join(parts).strip()


def resolve_channel_id(export_data: dict) -> int:
    if settings.TELEGRAM_CHANNEL_ID:
        return settings.TELEGRAM_CHANNEL_ID

    raw_id = export_data.get("id")
    if raw_id is None:
        return 0

    channel_id = int(raw_id)
    if channel_id < 0:
        return channel_id

    export_type = str(export_data.get("type", ""))
    if "channel" in export_type or "supergroup" in export_type:
        return int(f"-100{channel_id}")

    return -channel_id


def _has_product_signal(message: dict, caption: str) -> bool:
    if message.get("photo") or message.get("file"):
        return True
    lowered = caption.lower()
    return bool(caption) and ("🏷️" in caption or "грн" in lowered)


def _resolve_media_path(export_dir: Path, value: str) -> Path | None:
    cleaned = value.strip()
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = cleaned[1:-1].strip()

    candidates = [
        export_dir / cleaned,
        export_dir / "photos" / Path(cleaned).name,
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _load_photo_files(
    export_dir: Path, messages: list[dict]
) -> tuple[list[tuple[str, bytes]], list[tuple[int, int]]]:
    files: list[tuple[str, bytes]] = []
    sizes: list[tuple[int, int]] = []
    for message in messages:
        media_ref = message.get("photo") or message.get("file")
        if not media_ref:
            continue
        path = _resolve_media_path(export_dir, str(media_ref))
        if not path:
            logger.warning("Фото не знайдено: %s", media_ref)
            continue
        files.append((path.name, path.read_bytes()))
        sizes.append(
            (
                int(message.get("width") or 0),
                int(message.get("height") or 0),
            )
        )
    return files, sizes


def _normalize_caption_key(caption: str) -> str:
    return re.sub(r"\s+", " ", caption).strip()


def _is_album_sidecar_caption(caption: str, primary_caption: str) -> bool:
    """Порожній текст, дубль caption або коротка stock-нота до поточного товару."""
    from src.telegram_import.services.caption_selection import caption_quality_score

    cleaned = caption.strip()
    if not cleaned:
        return True

    primary = primary_caption.strip()
    if not primary:
        return False

    if _normalize_caption_key(cleaned) == _normalize_caption_key(primary):
        return True

    primary_score = caption_quality_score(primary)
    score = caption_quality_score(cleaned)
    if score <= primary_score - 10 and score < 20:
        return True
    return False


def _group_messages(messages: list[dict]) -> list[list[dict]]:
    """
    Caption-led групування: новий змістовний caption = новий товар.
    Порожні фото / stock-ноти / дубль caption приєднуються до поточного.
    (date_unixtime не використовуємо — bulk-forward зливає різні товари.)
    """
    sorted_messages = sorted(messages, key=lambda item: int(item.get("id", 0)))
    batches: list[list[dict]] = []
    seen_ids: set[int] = set()
    seen_groups: set[int] = set()
    album_buffer: list[dict] = []
    primary_caption = ""

    def flush_album() -> None:
        nonlocal album_buffer, primary_caption
        if album_buffer:
            batches.append(album_buffer)
        album_buffer = []
        primary_caption = ""

    for message in sorted_messages:
        message_id = int(message.get("id", 0))
        if not message_id or message_id in seen_ids:
            continue

        grouped_id = message.get("grouped_id")
        if grouped_id:
            flush_album()
            group_key = int(grouped_id)
            if group_key in seen_groups:
                continue
            group = [
                item
                for item in sorted_messages
                if item.get("grouped_id") == grouped_id
                and int(item.get("id", 0)) not in seen_ids
            ]
            for item in group:
                seen_ids.add(int(item["id"]))
            seen_groups.add(group_key)
            batches.append(sorted(group, key=lambda item: int(item["id"])))
            continue

        caption = flatten_export_text(message.get("text", ""))
        has_photo = bool(message.get("photo") or message.get("file"))
        if not has_photo and not caption:
            continue

        if album_buffer and _is_album_sidecar_caption(caption, primary_caption):
            album_buffer.append(message)
            seen_ids.add(message_id)
            if not primary_caption and caption:
                primary_caption = caption
            continue

        flush_album()
        album_buffer = [message]
        primary_caption = caption
        seen_ids.add(message_id)

    flush_album()
    return batches


def _build_post(export_dir: Path, messages: list[dict]) -> ExportPost | None:
    primary = min(messages, key=lambda item: int(item["id"]))
    caption = merge_message_captions(
        [flatten_export_text(message.get("text", "")) for message in messages]
    )

    photo_files, photo_sizes = _load_photo_files(export_dir, messages)
    photo_files = rank_photo_files(photo_files, sizes=photo_sizes)

    if not caption:
        if not photo_files:
            return None
        if len(messages) == 1:
            return None

    if not caption and not photo_files:
        return None

    media_group_id = str(primary.get("grouped_id") or "")
    return ExportPost(
        message_id=int(primary["id"]),
        caption=caption,
        media_group_id=media_group_id,
        photo_files=photo_files,
    )


def load_export_posts(export_dir: Path) -> tuple[dict, list[ExportPost]]:
    result_file = export_dir / "result.json"
    if not result_file.is_file():
        raise FileNotFoundError(f"Не знайдено {result_file}")

    export_data = json.loads(result_file.read_text(encoding="utf-8"))
    raw_messages = export_data.get("messages", [])
    candidates: list[dict] = []

    for message in raw_messages:
        if message.get("type") != "message":
            continue
        caption = flatten_export_text(message.get("text", ""))
        if not _has_product_signal(message, caption):
            continue
        candidates.append(message)

    posts: list[ExportPost] = []
    for batch in _group_messages(candidates):
        post = _build_post(export_dir, batch)
        if post:
            posts.append(post)

    return export_data, posts


def import_telegram_export(
    export_dir: Path,
    *,
    limit: int | None = None,
    dry_run: bool = False,
) -> ExportStats:
    export_data, posts = load_export_posts(export_dir)
    channel_id = resolve_channel_id(export_data)
    if not channel_id:
        raise ValueError(
            "Не вдалося визначити channel_id. Вкажи TELEGRAM_CHANNEL_ID у .env"
        )

    stats = ExportStats()
    max_message_id = 0

    if limit:
        posts = posts[:limit]

    for post in posts:
        stats.processed += 1
        max_message_id = max(max_message_id, post.message_id)

        if dry_run:
            stats.imported += 1
            continue

        try:
            record = import_telegram_message(
                channel_id=channel_id,
                message_id=post.message_id,
                caption=post.caption,
                photo_file_ids=[],
                media_group_id=post.media_group_id,
                photo_files=post.photo_files,
            )
        except ImportError as exc:
            stats.failed += 1
            stats.errors.append(f"{post.message_id}: {exc}")
            continue
        except Exception as exc:
            stats.failed += 1
            stats.errors.append(f"{post.message_id}: {exc}")
            logger.exception("Помилка імпорту export %s", post.message_id)
            continue

        if record.status == record.STATUS_IMPORTED:
            stats.imported += 1
        elif record.status == record.STATUS_SKIPPED:
            stats.skipped += 1
        else:
            stats.failed += 1
            if record.error:
                stats.errors.append(f"{post.message_id}: {record.error}")

    if not dry_run:
        state, _ = TelegramSyncState.objects.get_or_create(channel_id=channel_id)
        if max_message_id > state.last_message_id:
            state.last_message_id = max_message_id
        state.last_sync_at = timezone.now()
        state.save(update_fields=["last_message_id", "last_sync_at"])

    return stats
