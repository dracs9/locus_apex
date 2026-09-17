import json
import os
from pathlib import Path
from uuid import uuid4

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["SUPABASE_JWT_SECRET"] = "test-secret-at-least-32-bytes-long-000"
os.environ["LLM_API_KEY"] = ""
os.environ["CORS_ORIGINS"] = "http://localhost:5173"

import httpx  # noqa: E402
import jwt  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from sqlalchemy import insert  # noqa: E402

from app import db  # noqa: E402
from app.main import app  # noqa: E402
from app.schemas import University  # noqa: E402

SEED = Path(__file__).parents[3] / "supabase" / "seed"


def token_for(user_id: str) -> str:
    return jwt.encode({"sub": user_id, "aud": "authenticated", "role": "authenticated"},
                      os.environ["SUPABASE_JWT_SECRET"], algorithm="HS256")


@pytest_asyncio.fixture(scope="session", autouse=True)
async def database():
    await db.create_all()
    unis = json.loads((SEED / "universities.json").read_text(encoding="utf-8"))
    majors = json.loads((SEED / "majors.json").read_text(encoding="utf-8"))
    async with db.get_engine().begin() as conn:
        for u in unis:
            v = University.model_validate(u).model_dump(mode="json")
            core = {k: v.pop(k) for k in ("id", "name", "country", "city", "website", "world_rank")}
            await conn.execute(insert(db.universities).values(**core, data=v))
        for m in majors:
            await conn.execute(insert(db.majors).values(**m))
    yield


@pytest_asyncio.fixture
async def client():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def user():
    uid = str(uuid4())
    return {"id": uid, "headers": {"Authorization": f"Bearer {token_for(uid)}"}}
