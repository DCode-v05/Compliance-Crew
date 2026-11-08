"""Single entry point for all LLM calls — Groq only.

Every agent goes through ``llm_call()``. The wrapper handles:

- Structured output via a JSON schema hint + ``response_format=json_object``.
- Automatic audit logging of every call (the audit trail is built for free).
- Retries with exponential backoff, and fail-fast on permanent errors
  (auth / bad schema) so a misconfigured key doesn't waste time.

Provider: Groq Llama 3.3 70B (free tier, ~300 tok/s). Gemini was removed.
"""

from __future__ import annotations

import logging
import os
import re
import time
from hashlib import sha256
from typing import Any, Type, TypeVar

import json

from dotenv import load_dotenv
from pydantic import BaseModel

from src.db import log_audit_entry

load_dotenv()

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

_groq_client = None


def _get_groq_client():
    global _groq_client
    if _groq_client is not None:
        return _groq_client
    from groq import Groq

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set in environment")
    _groq_client = Groq(api_key=api_key)
    return _groq_client


def _hash_input(prompt: str) -> str:
    return sha256(prompt.encode()).hexdigest()[:16]


def _strip_code_fences(text: str) -> str:
    """Remove ```json ... ``` wrappers some models add despite instructions."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```\s*$", "", text)
    return text.strip()


_DROP_SCHEMA_KEYS = {
    "$defs",
    "title",
    "additionalProperties",
    "default",
    "maxLength",
    "minLength",
    "pattern",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "multipleOf",
}


def _clean_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Inline ``$defs`` and prune noisy keywords to keep the schema hint compact."""
    defs = schema.get("$defs", {})

    def resolve(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                ref = node["$ref"]
                if ref.startswith("#/$defs/"):
                    key = ref.split("/")[-1]
                    if key in defs:
                        return resolve(defs[key])
                return {}
            out: dict[str, Any] = {}
            for k, v in node.items():
                if k in _DROP_SCHEMA_KEYS:
                    continue
                out[k] = resolve(v)
            return out
        if isinstance(node, list):
            return [resolve(x) for x in node]
        return node

    cleaned = resolve(schema)
    cleaned.pop("$defs", None)
    return cleaned


def _is_permanent_error(err: Exception) -> bool:
    """True for errors that won't succeed on retry (auth, bad request, perms)."""
    msg = str(err).lower()
    markers = (
        "invalid authentication",
        "api key not valid",
        "api_key_invalid",
        "invalid api key",
        "permission_denied",
        "unauthenticated",
        "401",
        "403",
    )
    return any(m in msg for m in markers)


def llm_call(
    system_prompt: str,
    user_prompt: str,
    response_schema: Type[T],
    agent_name: str,
    max_retries: int = 3,
    temperature: float = 0.1,
) -> T:
    """Single entry point for all LLM calls (Groq).

    Args:
        system_prompt: System instruction.
        user_prompt: User-turn prompt.
        response_schema: Pydantic model the response must validate against.
        agent_name: Used for audit logging.
        max_retries: Attempts before giving up.
        temperature: Sampling temperature.

    Returns:
        Instance of ``response_schema``.

    Raises:
        RuntimeError: If the call fails after all retries.
    """
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            start = time.time()
            result = _call_groq(system_prompt, user_prompt, response_schema, temperature)
            latency_ms = int((time.time() - start) * 1000)
            log_audit_entry(
                agent_name=agent_name,
                input_hash=_hash_input(system_prompt + user_prompt),
                output_json=result.model_dump_json(),
                latency_ms=latency_ms,
                tokens_used=0,
                provider="groq",
            )
            return result
        except Exception as e:
            last_err = e
            logger.warning("[%s] groq attempt %d failed: %s", agent_name, attempt + 1, e)
            if _is_permanent_error(e):
                logger.info("[%s] groq error is permanent (auth/perms) — not retrying.", agent_name)
                break
            time.sleep(min(2**attempt, 8))

    raise RuntimeError(f"[{agent_name}] Groq call failed after retries: {last_err}") from last_err


def _call_groq(
    system_prompt: str,
    user_prompt: str,
    response_schema: Type[T],
    temperature: float,
) -> T:
    client = _get_groq_client()
    schema_hint = json.dumps(
        _clean_schema(response_schema.model_json_schema()), separators=(",", ":")
    )
    augmented_system = (
        system_prompt
        + "\n\n<schema>\nReturn ONLY valid JSON matching this schema. "
        + "No markdown fences, no preamble.\n"
        + schema_hint
        + "\n</schema>"
    )
    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": augmented_system},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=temperature,
    )
    text = _strip_code_fences(resp.choices[0].message.content or "")
    return response_schema.model_validate_json(text)


if __name__ == "__main__":
    from src.db import init_db

    init_db()

    class SmokeResp(BaseModel):
        answer: str

    try:
        result = llm_call(
            system_prompt="You are a helpful assistant. Respond with JSON.",
            user_prompt="Say 'hello world' as JSON with key 'answer'.",
            response_schema=SmokeResp,
            agent_name="smoke_test",
        )
        print("Groq OK:", result)
    except Exception as e:
        print("Groq smoke test failed:", e)
