"""Supabase Storage via its REST API (backend-only, private bucket).

The service key is sent as `apikey`; `Authorization: Bearer` is added only for legacy JWT service_role keys,
because the new `sb_secret_…` keys are not JWTs.
"""
import logging
from urllib.parse import quote

import httpx

from app.config import get_settings

log = logging.getLogger(__name__)
SIGNED_URL_TTL_S = 3600


class StorageNotConfigured(Exception):
    pass


class StorageError(Exception):
    pass


def _base() -> tuple[str, str, dict[str, str]]:
    s = get_settings()
    if not s.supabase_url or not s.supabase_service_key:
        raise StorageNotConfigured
    headers = {"apikey": s.supabase_service_key}
    if s.supabase_service_key.startswith("eyJ"):
        headers["Authorization"] = f"Bearer {s.supabase_service_key}"
    return f"{s.supabase_url.rstrip('/')}/storage/v1", s.storage_bucket, headers


async def upload(path: str, data: bytes, content_type: str) -> None:
    base, bucket, headers = _base()
    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(f"{base}/object/{bucket}/{quote(path)}", content=data,
                                headers={**headers, "Content-Type": content_type, "x-upsert": "false"})
    if res.status_code >= 300:
        raise StorageError(f"upload failed: HTTP {res.status_code} {res.text[:200]}")


async def sign_many(paths: list[str]) -> dict[str, str]:
    """{path: absolute signed URL}. Paths that fail to sign are left out."""
    if not paths:
        return {}
    base, bucket, headers = _base()
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.post(f"{base}/object/sign/{bucket}", headers=headers,
                                json={"paths": paths, "expiresIn": SIGNED_URL_TTL_S})
    if res.status_code >= 300:
        raise StorageError(f"sign failed: HTTP {res.status_code} {res.text[:200]}")
    out = {}
    root = base.removesuffix("/storage/v1")
    for item in res.json():
        signed = item.get("signedURL") or item.get("signedUrl")
        if signed and not item.get("error"):
            out[item["path"]] = signed if signed.startswith("http") else f"{root}/storage/v1{signed}"
    return out


async def remove(paths: list[str]) -> None:
    if not paths:
        return
    base, bucket, headers = _base()
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.request("DELETE", f"{base}/object/{bucket}", headers=headers, json={"prefixes": paths})
    if res.status_code >= 300:
        raise StorageError(f"remove failed: HTTP {res.status_code} {res.text[:200]}")


async def remove_quietly(paths: list[str]) -> None:
    """Cleanup must never break the user's request: log and continue."""
    try:
        await remove(paths)
    except (StorageNotConfigured, StorageError, httpx.HTTPError) as e:
        if paths:
            log.warning("could not remove %d stored files: %s", len(paths), e)
