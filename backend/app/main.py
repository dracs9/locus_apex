import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError
from sqlalchemy.exc import TimeoutError as SATimeoutError

from . import db
from .config import get_settings
from .routers import achievements, ai, catalog, demo, history, mentor, profile, recommendations, roadmap

logging.basicConfig(level=logging.INFO)

SEED_DIR = Path(__file__).resolve().parents[2] / "supabase" / "seed"


async def seed_sqlite() -> None:
    """Local dev without Supabase Postgres: create tables and load the catalog from supabase/seed."""
    from sqlalchemy import func, insert, select

    from .schemas import University

    await db.create_all()
    async with db.get_engine().begin() as conn:
        if (await conn.execute(select(func.count()).select_from(db.universities))).scalar_one() > 0:
            return
        if not SEED_DIR.exists():
            return
        for u in json.loads((SEED_DIR / "universities.json").read_text(encoding="utf-8")):
            data = University.model_validate(u).model_dump(mode="json")
            core = {k: data.pop(k) for k in ("id", "name", "country", "city", "website", "world_rank")}
            await conn.execute(insert(db.universities).values(**core, data=data))
        for m in json.loads((SEED_DIR / "majors.json").read_text(encoding="utf-8")):
            await conn.execute(insert(db.majors).values(**m))


@asynccontextmanager
async def lifespan(_: FastAPI):
    sqlite = get_settings().database_url.startswith("sqlite")
    if sqlite:
        await seed_sqlite()
    else:
        # Pay the handshake and the catalog read now, not inside the first user request.
        # Never fatal: an unreachable DB at boot must not kill the process, or the host's
        # health check flaps instead of reporting a degraded service.
        try:
            await db.warm_pool()
            from .services import catalog as catalog_service
            async with db.new_session() as session:
                await catalog_service.universities(session)
        except Exception:
            logging.getLogger("app").exception("Startup warm-up failed; serving anyway")
    try:
        yield
    finally:
        # Session-mode pooling pins a server backend per connection: without this, every
        # restart abandons the whole pool until the pooler reaps it. SQLite keeps its schema
        # in a StaticPool connection, so disposing there would wipe the test database.
        if not sqlite:
            await db.get_engine().dispose()


app = FastAPI(title="Applyra API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_list,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException):
    if isinstance(exc.detail, dict):
        return _error(exc.status_code, exc.detail.get("code", "ERROR"), exc.detail.get("message", ""))
    return _error(exc.status_code, "HTTP_ERROR", str(exc.detail))


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    where = ".".join(str(p) for p in first.get("loc", []))
    return _error(422, "VALIDATION_ERROR", f"{where}: {first.get('msg', 'invalid input')}")


DB_UNAVAILABLE = "База данных недоступна, попробуйте ещё раз"


@app.exception_handler(DBAPIError)
async def db_error(_: Request, exc: DBAPIError):
    """A dropped connection is transient: say so, so the client can retry instead of seeing a 500."""
    if exc.connection_invalidated:
        logging.getLogger("app").warning("DB connection lost: %s", exc)
        return _error(503, "DB_UNAVAILABLE", DB_UNAVAILABLE)
    logging.getLogger("app").exception("DB error", exc_info=exc)
    return _error(500, "INTERNAL_ERROR", "Что-то пошло не так на сервере")


@app.exception_handler(SATimeoutError)
async def db_busy(_: Request, exc: SATimeoutError):
    """Pool checkout timed out — every connection is busy."""
    logging.getLogger("app").warning("DB pool exhausted: %s", exc)
    return _error(503, "DB_UNAVAILABLE", DB_UNAVAILABLE)


@app.exception_handler(Exception)
async def unhandled_error(_: Request, exc: Exception):
    logging.getLogger("app").exception("Unhandled error", exc_info=exc)
    return _error(500, "INTERNAL_ERROR", "Что-то пошло не так на сервере")


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}


for r in (catalog, profile, achievements, recommendations, roadmap, history, demo, ai, mentor):
    app.include_router(r.router)
