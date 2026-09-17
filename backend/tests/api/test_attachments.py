from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app import db
from app.services import storage

from .conftest import token_for
from .test_api import PROFILE

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64


class FakeStorage:
    def __init__(self):
        self.files: dict[str, bytes] = {}
        self.removed: list[str] = []

    async def upload(self, path, data, content_type):
        self.files[path] = data

    async def sign_many(self, paths):
        return {p: f"https://storage.test/signed/{p}?token=t" for p in paths if p in self.files}

    async def remove(self, paths):
        self.removed += paths
        for p in paths:
            self.files.pop(p, None)


@pytest.fixture
def fake_storage(monkeypatch):
    fake = FakeStorage()
    monkeypatch.setattr(storage, "upload", fake.upload)
    monkeypatch.setattr(storage, "sign_many", fake.sign_many)
    monkeypatch.setattr(storage, "remove", fake.remove)
    return fake


async def make_achievement(client, user) -> str:
    await client.put("/me/profile", json={**PROFILE, "initial_achievements": []}, headers=user["headers"])
    r = await client.post("/me/achievements", json={"type": "OLYMPIAD", "title": "Олимпиада", "level": "national",
                                                    "date": "2026-03-01", "status": "done"}, headers=user["headers"])
    assert r.status_code == 200, r.text
    return r.json()["achievement_id"]


async def attachments_of(client, user, achievement_id):
    profile = (await client.get("/me/profile", headers=user["headers"])).json()
    return next(a for a in profile["achievements"] if a["id"] == achievement_id)["attachments"]


async def snapshot_count() -> int:
    async with db.get_engine().connect() as conn:
        return (await conn.execute(select(func.count()).select_from(db.snapshots))).scalar_one()


async def test_link_add_list_delete(client, user, fake_storage):
    aid = await make_achievement(client, user)
    before = await snapshot_count()
    r = await client.post(f"/me/achievements/{aid}/attachments/link",
                          json={"url": "https://github.com/me/project", "title": "Проект"}, headers=user["headers"])
    assert r.status_code == 201, r.text
    link = r.json()
    assert link["kind"] == "link" and link["url"] == "https://github.com/me/project"
    assert [a["id"] for a in await attachments_of(client, user, aid)] == [link["id"]]
    assert await snapshot_count() == before  # attachments never trigger a recomputation

    r = await client.delete(f"/me/achievements/{aid}/attachments/{link['id']}", headers=user["headers"])
    assert r.status_code == 204
    assert await attachments_of(client, user, aid) == []


@pytest.mark.parametrize("bad", ["javascript:alert(1)", "not a url", "ftp://example.com/file"])
async def test_link_rejects_unsafe_urls(client, user, fake_storage, bad):
    aid = await make_achievement(client, user)
    r = await client.post(f"/me/achievements/{aid}/attachments/link", json={"url": bad}, headers=user["headers"])
    assert r.status_code == 422


async def test_photo_upload_is_signed_in_profile(client, user, fake_storage):
    aid = await make_achievement(client, user)
    r = await client.post(f"/me/achievements/{aid}/attachments/photo", files={"file": ("diploma.png", PNG, "image/png")},
                          headers=user["headers"])
    assert r.status_code == 201, r.text
    photo = r.json()
    assert photo["kind"] == "photo" and photo["content_type"] == "image/png"
    path = next(iter(fake_storage.files))
    assert path.startswith(f"{user['id']}/{aid}/") and path.endswith(".png")
    listed = await attachments_of(client, user, aid)
    assert listed[0]["url"].startswith("https://storage.test/signed/")


async def test_photo_rejects_non_images_and_large_files(client, user, fake_storage):
    aid = await make_achievement(client, user)
    r = await client.post(f"/me/achievements/{aid}/attachments/photo",
                          files={"file": ("evil.png", b"<script>alert(1)</script>", "image/png")}, headers=user["headers"])
    assert r.status_code == 415 and r.json()["error"]["code"] == "UNSUPPORTED_FILE"
    big = JPEG + b"\x00" * (5 * 1024 * 1024)
    r = await client.post(f"/me/achievements/{aid}/attachments/photo", files={"file": ("big.jpg", big, "image/jpeg")},
                          headers=user["headers"])
    assert r.status_code == 413 and r.json()["error"]["code"] == "FILE_TOO_LARGE"
    assert fake_storage.files == {}


async def test_limit_of_five(client, user, fake_storage):
    aid = await make_achievement(client, user)
    for i in range(5):
        r = await client.post(f"/me/achievements/{aid}/attachments/link", json={"url": f"https://ex.com/{i}"},
                              headers=user["headers"])
        assert r.status_code == 201
    r = await client.post(f"/me/achievements/{aid}/attachments/photo", files={"file": ("a.jpg", JPEG, "image/jpeg")},
                          headers=user["headers"])
    assert r.status_code == 409 and r.json()["error"]["code"] == "ATTACHMENT_LIMIT"


async def test_other_user_cannot_touch_attachments(client, user, fake_storage):
    aid = await make_achievement(client, user)
    link = (await client.post(f"/me/achievements/{aid}/attachments/link", json={"url": "https://ex.com"},
                              headers=user["headers"])).json()
    other = {"Authorization": f"Bearer {token_for(str(uuid4()))}"}
    r = await client.post(f"/me/achievements/{aid}/attachments/link", json={"url": "https://ex.com/x"}, headers=other)
    assert r.status_code == 404
    r = await client.delete(f"/me/achievements/{aid}/attachments/{link['id']}", headers=other)
    assert r.status_code == 404
    assert len(await attachments_of(client, user, aid)) == 1


async def test_deleting_achievement_and_reset_remove_files(client, user, fake_storage):
    aid = await make_achievement(client, user)
    await client.post(f"/me/achievements/{aid}/attachments/photo", files={"file": ("a.jpg", JPEG, "image/jpeg")},
                      headers=user["headers"])
    path = next(iter(fake_storage.files))
    r = await client.delete(f"/me/achievements/{aid}", headers=user["headers"])
    assert r.status_code == 200 and path in fake_storage.removed

    aid2 = await make_achievement(client, user)
    await client.post(f"/me/achievements/{aid2}/attachments/photo", files={"file": ("b.png", PNG, "image/png")},
                      headers=user["headers"])
    path2 = next(iter(fake_storage.files))
    assert (await client.post("/me/reset", headers=user["headers"])).status_code == 200
    assert path2 in fake_storage.removed and fake_storage.files == {}


async def test_photo_without_storage_config_returns_503(client, user, monkeypatch):
    aid = await make_achievement(client, user)

    async def not_configured(*_args, **_kwargs):
        raise storage.StorageNotConfigured

    monkeypatch.setattr(storage, "upload", not_configured)
    r = await client.post(f"/me/achievements/{aid}/attachments/photo", files={"file": ("a.jpg", JPEG, "image/jpeg")},
                          headers=user["headers"])
    assert r.status_code == 503 and r.json()["error"]["code"] == "STORAGE_NOT_CONFIGURED"
