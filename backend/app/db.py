"""SQLAlchemy Core tables mirroring supabase/migrations (Postgres in prod, SQLite in tests)."""
from collections.abc import AsyncIterator

from sqlalchemy import (JSON, Boolean, Column, Date, DateTime, Float, Integer, MetaData, String, Table, Text, Uuid)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from .config import get_settings

metadata = MetaData()
Json = JSON().with_variant(JSONB(), "postgresql")
TextArray = JSON().with_variant(ARRAY(Text), "postgresql")

universities = Table(
    "universities", metadata,
    Column("id", Text, primary_key=True),
    Column("name", Text, nullable=False),
    Column("country", Text, nullable=False),
    Column("city", Text, nullable=False),
    Column("website", Text, nullable=False),
    Column("world_rank", Integer, nullable=False),
    Column("data", Json, nullable=False),
)

majors = Table(
    "majors", metadata,
    Column("id", Text, primary_key=True),
    Column("name_ru", Text, nullable=False),
    Column("name_en", Text, nullable=False),
    Column("cip_codes", TextArray, nullable=False),
)

profiles = Table(
    "profiles", metadata,
    Column("user_id", Uuid, primary_key=True),
    Column("data", Json, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

achievements = Table(
    "achievements", metadata,
    Column("id", Uuid, primary_key=True),
    Column("user_id", Uuid, nullable=False, index=True),
    Column("type", Text, nullable=False),
    Column("score", Float),
    Column("title", Text),
    Column("level", Text),
    Column("date", Date, nullable=False),
    Column("status", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

favorites = Table(
    "favorites", metadata,
    Column("user_id", Uuid, primary_key=True),
    Column("university_id", Text, primary_key=True),
)

roadmap_progress = Table(
    "roadmap_progress", metadata,
    Column("user_id", Uuid, primary_key=True),
    Column("step_id", Text, primary_key=True),
    Column("done", Boolean, nullable=False),
    Column("done_at", DateTime(timezone=True)),
)

snapshots = Table(
    "snapshots", metadata,
    Column("id", Uuid, primary_key=True),
    Column("user_id", Uuid, nullable=False, index=True),
    Column("at", DateTime(timezone=True), nullable=False),
    Column("result", Json, nullable=False),
    Column("roadmap_step_ids", TextArray, nullable=False),
    Column("profile_hash", String, nullable=False),
    Column("cause", Text, nullable=False),
    Column("diff", Json),
)

llm_cache = Table(
    "llm_cache", metadata,
    Column("key", Text, primary_key=True),
    Column("value", Json, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine, _sessionmaker
    if _engine is None:
        url = get_settings().database_url
        if url.startswith("sqlite"):
            _engine = create_async_engine(url, poolclass=StaticPool, connect_args={"check_same_thread": False})
        else:
            # statement_cache_size=0 keeps asyncpg compatible with Supabase's transaction pooler
            _engine = create_async_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=5,
                                          connect_args={"statement_cache_size": 0})
        _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


async def get_session() -> AsyncIterator[AsyncSession]:
    get_engine()
    assert _sessionmaker is not None
    async with _sessionmaker() as session:
        yield session


async def create_all() -> None:
    """Used for SQLite (tests / local without Supabase). Postgres uses supabase/migrations."""
    async with get_engine().begin() as conn:
        await conn.run_sync(metadata.create_all)
