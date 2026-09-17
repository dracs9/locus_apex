"""Auth: verify the Supabase JWT and use `sub` as the user id."""
from functools import lru_cache
from uuid import UUID

import jwt
from fastapi import Header, HTTPException
from starlette.concurrency import run_in_threadpool

from .config import get_settings
from .db import get_session  # noqa: F401  (re-exported for routers)


@lru_cache
def _jwks_client(url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(url, cache_keys=True, lifespan=3600)


async def decode_token(token: str) -> dict:
    settings = get_settings()
    try:
        alg = jwt.get_unverified_header(token).get("alg")
        if alg == "HS256":
            if not settings.supabase_jwt_secret:
                raise jwt.InvalidTokenError("HS256 token but SUPABASE_JWT_SECRET is not set")
            key = settings.supabase_jwt_secret
        else:
            if not settings.supabase_url:
                raise jwt.InvalidTokenError("SUPABASE_URL is not set")
            client = _jwks_client(f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json")
            key = (await run_in_threadpool(client.get_signing_key_from_jwt, token)).key
        return jwt.decode(token, key, algorithms=["HS256", "ES256", "RS256"], audience="authenticated")
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail={"code": "INVALID_TOKEN", "message": str(e)}) from e


async def get_user_id(authorization: str | None = Header(default=None)) -> UUID:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "Missing bearer token"})
    claims = await decode_token(authorization.split(" ", 1)[1])
    try:
        return UUID(claims["sub"])
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=401, detail={"code": "INVALID_TOKEN", "message": "Token has no valid sub"}) from e
