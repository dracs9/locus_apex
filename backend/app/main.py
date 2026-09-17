import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import db
from .config import get_settings
from .routers import achievements, ai, catalog, demo, history, profile, recommendations, roadmap

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
    if get_settings().database_url.startswith("sqlite"):
        await seed_sqlite()
    yield


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


@app.exception_handler(Exception)
async def unhandled_error(_: Request, exc: Exception):
    logging.getLogger("app").exception("Unhandled error", exc_info=exc)
    return _error(500, "INTERNAL_ERROR", "Что-то пошло не так на сервере")


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}


for r in (catalog, profile, achievements, recommendations, roadmap, history, demo, ai):
    app.include_router(r.router)
