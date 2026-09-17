"""Photos and links attached to achievements. They never affect scoring, so no recomputation happens here."""
import logging
from uuid import UUID, uuid4

import httpx
from fastapi import HTTPException
from sqlalchemy import delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import db
from app.schemas import MAX_ATTACHMENTS, MAX_PHOTO_BYTES, Attachment, LinkIn

from . import storage
from .profiles import now

log = logging.getLogger(__name__)

T = db.achievement_attachments


def sniff_image(data: bytes) -> tuple[str, str] | None:
    """(content_type, extension) from magic bytes; None if not a supported image."""
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", "webp"
    if data[4:8] == b"ftyp" and data[8:12] in (b"heic", b"heix", b"hevc", b"hevx", b"mif1", b"msf1", b"heif"):
        return ("image/heif", "heif") if data[8:12] in (b"mif1", b"msf1", b"heif") else ("image/heic", "heic")
    return None


def _error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


async def _require_achievement(session: AsyncSession, user_id: UUID, achievement_id: UUID) -> None:
    found = (await session.execute(select(db.achievements.c.id).where(
        db.achievements.c.id == achievement_id, db.achievements.c.user_id == user_id))).first()
    if not found:
        raise _error(404, "ACHIEVEMENT_NOT_FOUND", "Достижение не найдено")


async def _check_limit(session: AsyncSession, user_id: UUID, achievement_id: UUID) -> None:
    count = (await session.execute(select(func.count()).select_from(T).where(
        T.c.achievement_id == achievement_id, T.c.user_id == user_id))).scalar_one()
    if count >= MAX_ATTACHMENTS:
        raise _error(409, "ATTACHMENT_LIMIT", f"К достижению можно прикрепить не больше {MAX_ATTACHMENTS} файлов и ссылок")


def _to_model(r, signed: dict[str, str]) -> Attachment:
    url = r.url if r.kind == "link" else signed.get(r.storage_path)
    return Attachment(id=r.id, kind=r.kind, url=url, title=r.title, content_type=r.content_type, created_at=r.created_at)


async def list_for(session: AsyncSession, user_id: UUID) -> dict[UUID, list[Attachment]]:
    rows = (await session.execute(select(T).where(T.c.user_id == user_id).order_by(T.c.created_at, T.c.id))).all()
    photo_paths = [r.storage_path for r in rows if r.kind == "photo"]
    signed: dict[str, str] = {}
    if photo_paths:
        try:
            signed = await storage.sign_many(photo_paths)
        except (storage.StorageNotConfigured, storage.StorageError, httpx.HTTPError) as e:
            log.warning("could not sign photo URLs: %s", e)  # photos are listed without a URL, the UI shows a placeholder
    out: dict[UUID, list[Attachment]] = {}
    for r in rows:
        out.setdefault(r.achievement_id, []).append(_to_model(r, signed))
    return out


async def add_link(session: AsyncSession, user_id: UUID, achievement_id: UUID, body: LinkIn) -> Attachment:
    await _require_achievement(session, user_id, achievement_id)
    await _check_limit(session, user_id, achievement_id)
    url = str(body.url)
    if not url.lower().startswith(("http://", "https://")):
        raise _error(422, "INVALID_URL", "Ссылка должна начинаться с http:// или https://")
    row = {"id": uuid4(), "achievement_id": achievement_id, "user_id": user_id, "kind": "link", "url": url,
           "title": (body.title or "").strip() or None, "created_at": now()}
    await session.execute(insert(T).values(**row))
    await session.commit()
    return Attachment(id=row["id"], kind="link", url=url, title=row["title"], created_at=row["created_at"])


async def add_photo(session: AsyncSession, user_id: UUID, achievement_id: UUID, data: bytes,
                    title: str | None) -> Attachment:
    await _require_achievement(session, user_id, achievement_id)
    await _check_limit(session, user_id, achievement_id)
    if len(data) > MAX_PHOTO_BYTES:
        raise _error(413, "FILE_TOO_LARGE", "Фото должно быть не больше 5 МБ")
    kind = sniff_image(data)
    if kind is None:
        raise _error(415, "UNSUPPORTED_FILE", "Поддерживаются фото JPG, PNG, WebP или HEIC")
    content_type, ext = kind
    attachment_id = uuid4()
    path = f"{user_id}/{achievement_id}/{attachment_id}.{ext}"
    try:
        await storage.upload(path, data, content_type)
    except storage.StorageNotConfigured:
        raise _error(503, "STORAGE_NOT_CONFIGURED", "Загрузка фото не настроена на сервере")
    except (storage.StorageError, httpx.HTTPError) as e:
        log.warning("photo upload failed: %s", e)
        raise _error(502, "STORAGE_ERROR", "Не удалось сохранить фото, попробуйте ещё раз")
    created = now()
    title = (title or "").strip()[:120] or None
    try:
        await session.execute(insert(T).values(id=attachment_id, achievement_id=achievement_id, user_id=user_id,
                                               kind="photo", storage_path=path, title=title,
                                               content_type=content_type, size_bytes=len(data), created_at=created))
        await session.commit()
    except Exception:
        await storage.remove_quietly([path])
        raise
    try:
        url = (await storage.sign_many([path])).get(path)
    except (storage.StorageError, httpx.HTTPError):
        url = None
    return Attachment(id=attachment_id, kind="photo", url=url, title=title, content_type=content_type, created_at=created)


async def delete_one(session: AsyncSession, user_id: UUID, achievement_id: UUID, attachment_id: UUID) -> None:
    row = (await session.execute(select(T).where(T.c.id == attachment_id, T.c.achievement_id == achievement_id,
                                                 T.c.user_id == user_id))).first()
    if row is None:
        raise _error(404, "ATTACHMENT_NOT_FOUND", "Вложение не найдено")
    await session.execute(delete(T).where(T.c.id == attachment_id, T.c.user_id == user_id))
    await session.commit()
    if row.kind == "photo":
        await storage.remove_quietly([row.storage_path])


async def photo_paths(session: AsyncSession, user_id: UUID, achievement_id: UUID | None = None) -> list[str]:
    q = select(T.c.storage_path).where(T.c.user_id == user_id, T.c.kind == "photo")
    if achievement_id is not None:
        q = q.where(T.c.achievement_id == achievement_id)
    return [r[0] for r in (await session.execute(q)).all()]
