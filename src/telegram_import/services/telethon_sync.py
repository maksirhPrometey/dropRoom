import asyncio
import logging
from dataclasses import dataclass, field
from io import BytesIO

from django.conf import settings
from telethon import utils
from telethon.tl.types import Message

from src.telegram_import.models import TelegramSyncState
from src.telegram_import.services.caption_selection import merge_message_captions
from src.telegram_import.services.importer import ImportError, import_telegram_message
from src.telegram_import.services.telethon_client import TelethonConfigError, get_telethon_client

logger = logging.getLogger("src.telegram_import")


@dataclass
class SyncStats:
    processed: int = 0
    imported: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class ChannelPost:
    channel_id: int
    message_id: int
    caption: str
    media_group_id: str
    photo_files: list[tuple[str, bytes]]


def _normalize_channel_ref(channel_id: int | None, channel_username: str) -> str | int:
    if channel_id:
        return channel_id
    username = (channel_username or "").strip().lstrip("@")
    if username:
        return username
    raise TelethonConfigError(
        "Вкажи TELEGRAM_CHANNEL_ID або TELEGRAM_CHANNEL_USERNAME у .env"
    )


def _message_caption(message: Message) -> str:
    return (message.message or message.text or "").strip()


def _has_product_signal(message: Message) -> bool:
    if message.photo:
        return True
    caption = _message_caption(message)
    return bool(caption) and ("🏷️" in caption or "грн" in caption.lower())


async def _download_photos(client, messages: list[Message]) -> list[tuple[str, bytes]]:
    files: list[tuple[str, bytes]] = []
    for message in messages:
        if not message.photo:
            continue
        buffer = BytesIO()
        await client.download_media(message, file=buffer)
        content = buffer.getvalue()
        if not content:
            continue
        filename = f"tg-{message.id}.jpg"
        files.append((filename, content))
    return files


def _group_messages(messages: list[Message]) -> list[list[Message]]:
    batches: list[list[Message]] = []
    seen_ids: set[int] = set()
    seen_groups: set[int] = set()

    for message in messages:
        if message.id in seen_ids:
            continue

        if message.grouped_id:
            group_id = int(message.grouped_id)
            if group_id in seen_groups:
                continue
            group = [
                item
                for item in messages
                if item.grouped_id == message.grouped_id and item.id not in seen_ids
            ]
            for item in group:
                seen_ids.add(item.id)
            seen_groups.add(group_id)
            batches.append(sorted(group, key=lambda item: item.id))
            continue

        seen_ids.add(message.id)
        batches.append([message])

    return batches


async def _build_post(
    client, messages: list[Message], *, dry_run: bool = False
) -> ChannelPost | None:
    primary = min(messages, key=lambda item: item.id)
    channel_id = int(primary.chat_id)
    caption = merge_message_captions(
        [_message_caption(message) for message in messages]
    )

    photo_files: list[tuple[str, bytes]] = []
    if not dry_run:
        photo_files = await _download_photos(client, messages)
    elif any(message.photo for message in messages):
        photo_files = [("dry-run.jpg", b"")]
    if not caption and not photo_files:
        return None

    media_group_id = str(primary.grouped_id or "")
    return ChannelPost(
        channel_id=channel_id,
        message_id=int(primary.id),
        caption=caption,
        media_group_id=media_group_id,
        photo_files=photo_files,
    )


async def _sync_channel_async(
    *,
    channel_id: int | None,
    channel_username: str,
    limit: int | None,
    full: bool,
    dry_run: bool,
) -> tuple[SyncStats, int]:
    stats = SyncStats()
    channel_ref = _normalize_channel_ref(channel_id, channel_username)

    async with get_telethon_client() as client:
        entity = await client.get_entity(channel_ref)
        resolved_channel_id = utils.get_peer_id(entity)
        state, _ = await asyncio.to_thread(
            TelegramSyncState.objects.get_or_create,
            channel_id=resolved_channel_id,
        )

        min_id = 0 if full else int(state.last_message_id)
        kwargs: dict = {
            "entity": entity,
            "reverse": full,
            "min_id": min_id,
        }
        if limit:
            kwargs["limit"] = limit

        messages: list[Message] = []
        async for message in client.iter_messages(**kwargs):
            if not isinstance(message, Message):
                continue
            if not _has_product_signal(message):
                continue
            messages.append(message)

        batches = _group_messages(messages)
        max_message_id = state.last_message_id

        for batch in batches:
            stats.processed += 1
            post = await _build_post(client, batch, dry_run=dry_run)
            if not post:
                stats.skipped += 1
                continue

            max_message_id = max(max_message_id, post.message_id)

            if dry_run:
                stats.imported += 1
                continue

            try:
                record = await asyncio.to_thread(
                    import_telegram_message,
                    channel_id=post.channel_id,
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
                logger.exception("Помилка імпорту TG %s", post.message_id)
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
            from django.utils import timezone

            await asyncio.to_thread(
                TelegramSyncState.objects.filter(pk=state.pk).update,
                last_message_id=max_message_id,
                last_sync_at=timezone.now(),
            )

        return stats, resolved_channel_id


def sync_telegram_channel(
    *,
    channel_id: int | None = None,
    channel_username: str = "",
    limit: int | None = None,
    full: bool = False,
    dry_run: bool = False,
) -> tuple[SyncStats, int]:
    channel_id = channel_id or settings.TELEGRAM_CHANNEL_ID or None
    channel_username = channel_username or settings.TELEGRAM_CHANNEL_USERNAME
    return asyncio.run(
        _sync_channel_async(
            channel_id=channel_id,
            channel_username=channel_username,
            limit=limit,
            full=full,
            dry_run=dry_run,
        )
    )
