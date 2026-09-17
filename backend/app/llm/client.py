"""Gemini client. Any failure (no key, timeout, invalid JSON) returns None so callers use fallbacks."""
import asyncio
import json
import logging

from app.config import get_settings

log = logging.getLogger(__name__)
_client = None


def _get_client():
    global _client
    if _client is None:
        from google import genai

        _client = genai.Client(api_key=get_settings().llm_api_key)
    return _client


async def generate_json(system: str, payload: dict) -> dict | list | None:
    settings = get_settings()
    if not settings.llm_api_key:
        return None
    try:
        from google.genai import types

        response = await asyncio.wait_for(
            _get_client().aio.models.generate_content(
                model=settings.llm_model,
                contents=json.dumps(payload, ensure_ascii=False),
                config=types.GenerateContentConfig(system_instruction=system, response_mime_type="application/json",
                                                   temperature=0.2),
            ),
            timeout=settings.llm_timeout_s,
        )
        return json.loads(response.text or "")
    except Exception as e:  # noqa: BLE001 — the LLM is optional, never break the request
        log.warning("LLM call failed: %s", e)
        return None
