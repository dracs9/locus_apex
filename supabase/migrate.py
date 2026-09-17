"""Apply supabase/migrations/*.sql in order to DATABASE_URL (reads backend/.env).

Usage (from repo root):  backend/.venv/Scripts/python supabase/migrate.py
Alternatively paste the SQL files into the Supabase SQL editor.
"""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import asyncpg  # noqa: E402

from app.config import Settings  # noqa: E402


def plain_dsn(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://")


async def main() -> None:
    settings = Settings(_env_file=ROOT / "backend" / ".env")
    if not settings.database_url.startswith("postgresql"):
        sys.exit("DATABASE_URL must be a Postgres URL (see backend/.env.example)")
    conn = await asyncpg.connect(plain_dsn(settings.database_url), statement_cache_size=0)
    try:
        for path in sorted((ROOT / "supabase" / "migrations").glob("*.sql")):
            print(f"applying {path.name}")
            await conn.execute(path.read_text(encoding="utf-8"))
    finally:
        await conn.close()
    print("done")


if __name__ == "__main__":
    asyncio.run(main())
