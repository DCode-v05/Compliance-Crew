"""Tests for the SHA-256 audit hash chain (pure logic + DB integration)."""

from __future__ import annotations

from src.utils.audit_chain import (
    GENESIS_HASH,
    canonical_payload,
    compute_entry_hash,
    verify_chain,
)


def _row(entry_id, prev_hash, *, agent="mapper", out='{"a":1}', ts="2026-01-01T00:00:00+00:00"):
    payload = canonical_payload(entry_id, agent, "ih", out, 10, "groq", ts)
    return {
        "entry_id": entry_id,
        "agent_name": agent,
        "input_hash": "ih",
        "output_json": out,
        "latency_ms": 10,
        "provider": "groq",
        "timestamp": ts,
        "prev_hash": prev_hash,
        "entry_hash": compute_entry_hash(prev_hash, payload),
    }


def test_empty_chain_is_intact():
    result = verify_chain([])
    assert result.intact is True
    assert result.total == 0


def test_valid_chain_verifies():
    r1 = _row("a", GENESIS_HASH)
    r2 = _row("b", r1["entry_hash"])
    r3 = _row("c", r2["entry_hash"])
    result = verify_chain([r1, r2, r3])
    assert result.intact is True
    assert result.broken_at is None


def test_tampered_output_breaks_chain():
    r1 = _row("a", GENESIS_HASH)
    r2 = _row("b", r1["entry_hash"])
    r2["output_json"] = '{"a":999}'
    result = verify_chain([r1, r2])
    assert result.intact is False
    assert result.broken_at == 2


def test_reordered_rows_break_chain():
    r1 = _row("a", GENESIS_HASH)
    r2 = _row("b", r1["entry_hash"])
    result = verify_chain([r2, r1])
    assert result.intact is False
    assert result.broken_at == 1


def test_db_logging_extends_intact_chain(tmp_db):
    from src import db

    db.log_audit_entry("mapper", "h1", '{"x":1}', 12, 0, "groq", db_path=tmp_db)
    db.log_audit_entry("validator", "h2", '{"y":2}', 8, 0, "groq", db_path=tmp_db)
    result = db.verify_audit_chain(db_path=tmp_db)
    assert result["intact"] is True
    assert result["total"] == 2
