"""LLM wrapper tests — schema cleaning and code-fence stripping.

These tests do NOT make real API calls. The wrapper's network paths are
exercised via the manual smoke test in ``python -m src.llm``."""

from __future__ import annotations

from pydantic import BaseModel

from src.llm import _clean_schema, _hash_input, _is_permanent_error, _strip_code_fences
from src.state import MAP


def test_strip_code_fences_removes_json_block():
    text = '```json\n{"answer": "hi"}\n```'
    assert _strip_code_fences(text) == '{"answer": "hi"}'


def test_strip_code_fences_removes_bare_fence():
    text = '```\n{"k": 1}\n```'
    assert _strip_code_fences(text) == '{"k": 1}'


def test_strip_code_fences_passthrough_clean_json():
    text = '{"answer": "hi"}'
    assert _strip_code_fences(text) == '{"answer": "hi"}'


def test_clean_schema_removes_defs_and_inlines_refs():
    schema = MAP.model_json_schema()
    cleaned = _clean_schema(schema)
    assert "$defs" not in cleaned
    import json as _json

    serialised = _json.dumps(cleaned)
    assert "$ref" not in serialised
    assert "$defs" not in serialised


def test_clean_schema_keeps_enums():
    schema = MAP.model_json_schema()
    cleaned = _clean_schema(schema)
    assert "properties" in cleaned


def test_clean_schema_drops_title_and_additional_properties():
    class Inner(BaseModel):
        x: int

    schema = Inner.model_json_schema()
    cleaned = _clean_schema(schema)
    assert "title" not in cleaned
    assert "additionalProperties" not in cleaned


def test_clean_schema_strips_unsupported_constraints():
    import json as _json

    serialised = _json.dumps(_clean_schema(MAP.model_json_schema()))
    for kw in ("maxLength", "minLength", "minimum", "maximum"):
        assert f'"{kw}"' not in serialised


def test_is_permanent_error_classification():
    assert _is_permanent_error(Exception("401 invalid authentication")) is True
    assert _is_permanent_error(Exception("API key not valid")) is True
    assert _is_permanent_error(Exception("429 rate limit exceeded")) is False


def test_hash_input_stable_and_short():
    h = _hash_input("hello world")
    assert len(h) == 16
    assert _hash_input("hello world") == h
    assert _hash_input("hello world ") != h
