"""Gemini chat with function calling for the mentor. `model_step` is the only thing that talks to the model;
tests replace it with a script. Any failure returns None so the caller falls back to template text."""
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from app.config import get_settings

from .client import _get_client

log = logging.getLogger(__name__)


@dataclass
class ToolCall:
    name: str
    args: dict[str, Any]


@dataclass
class ModelTurn:
    text: str = ""
    calls: list[ToolCall] = field(default_factory=list)
    raw: Any = None  # the model's native content, sent back as-is (keeps Gemini's thought signatures)


# History entries: {"role": "user"|"model", "text"} | {"role": "model", "calls", "raw"} | {"role": "tool", "results"}
History = list[dict[str, Any]]


def _contents(history: History):
    from google.genai import types

    out = []
    for h in history:
        if h["role"] == "tool":
            out.append(types.Content(role="user", parts=[
                types.Part.from_function_response(name=name, response={"result": result})
                for name, result in h["results"]]))
        elif h.get("raw") is not None:
            out.append(h["raw"])
        elif h.get("calls"):
            out.append(types.Content(role="model", parts=[
                types.Part.from_function_call(name=c.name, args=c.args) for c in h["calls"]]))
        else:
            out.append(types.Content(role=h["role"], parts=[types.Part.from_text(text=h["text"])]))
    return out


async def model_step(system: str, history: History, tools: list[dict]) -> ModelTurn | None:
    settings = get_settings()
    if not settings.llm_api_key:
        return None
    try:
        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.3,
            tools=[types.Tool(function_declarations=[types.FunctionDeclaration(**t) for t in tools])],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        response = await asyncio.wait_for(
            _get_client().aio.models.generate_content(model=settings.llm_model, contents=_contents(history),
                                                      config=config),
            timeout=settings.llm_mentor_timeout_s,
        )
        calls = [ToolCall(name=c.name, args=dict(c.args or {})) for c in (response.function_calls or [])]
        raw = response.candidates[0].content if response.candidates else None
        text = "" if calls else (response.text or "")
        return ModelTurn(text=text.strip(), calls=calls, raw=raw)
    except Exception as e:  # noqa: BLE001 — the LLM is optional, never break the request
        log.warning("mentor LLM call failed: %s", e)
        return None
