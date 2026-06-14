"""SQLite persistence tests (audit trail, maps, validations, assignments)."""

from __future__ import annotations

from src.db import (
    get_connection,
    log_audit_entry,
    save_assignment,
    save_escalation,
    save_map,
    save_validation,
)
from src.state import MAP, Assignment, Citation, Escalation, Validation


def _citation() -> Citation:
    return Citation(
        paragraph_id="p-1",
        verbatim_quote="shall do the thing",
        confidence=0.9,
        source_doc_id="doc",
    )


def test_log_audit_entry_roundtrip(tmp_db):
    entry_id = log_audit_entry(
        agent_name="mapper",
        input_hash="abc123",
        output_json='{"k":"v"}',
        latency_ms=120,
        tokens_used=42,
        provider="groq",
        db_path=tmp_db,
    )
    assert entry_id

    conn = get_connection(tmp_db)
    try:
        rows = conn.execute("SELECT * FROM audit_entries").fetchall()
    finally:
        conn.close()
    assert len(rows) == 1
    assert rows[0]["agent_name"] == "mapper"
    assert rows[0]["latency_ms"] == 120
    assert rows[0]["provider"] == "groq"
    # Chain columns are populated.
    assert rows[0]["entry_hash"]


def test_save_map_and_validation_relate(tmp_db):
    m = MAP(
        map_id="map-1",
        paragraph_id="p-1",
        control_title="t",
        control_description="d",
        evidence_type="customer_record",
        risk_category="high",
        citation=_citation(),
    )
    save_map(m, db_path=tmp_db)

    v = Validation(
        validation_id="val-1",
        map_id="map-1",
        verdict="approved",
        reasoning="ok",
        cited_text="shall do the thing",
    )
    save_validation(v, db_path=tmp_db)

    conn = get_connection(tmp_db)
    try:
        maps = conn.execute("SELECT * FROM maps").fetchall()
        vals = conn.execute("SELECT * FROM validations").fetchall()
    finally:
        conn.close()
    assert len(maps) == 1 and maps[0]["control_title"] == "t"
    assert len(vals) == 1 and vals[0]["map_id"] == "map-1"


def test_save_assignment_and_escalation(tmp_db):
    # Parent MAP must exist first (assignments/escalations FK -> maps).
    save_map(
        MAP(
            map_id="map-1",
            paragraph_id="p-1",
            control_title="t",
            control_description="d",
            evidence_type="customer_record",
            risk_category="high",
            citation=_citation(),
        ),
        db_path=tmp_db,
    )
    a = Assignment(
        assignment_id="a-1",
        map_id="map-1",
        department="Retail Banking",
        priority="urgent",
        deadline_days=30,
        dependencies=["map-2"],
        rationale="r",
    )
    save_assignment(a, db_path=tmp_db)
    e = Escalation(
        escalation_id="e-1",
        map_id="map-1",
        severity="high",
        reason="high-risk control",
        deadline_days=30,
    )
    save_escalation(e, db_path=tmp_db)

    conn = get_connection(tmp_db)
    try:
        assigns = conn.execute("SELECT * FROM assignments").fetchall()
        escs = conn.execute("SELECT * FROM escalations").fetchall()
    finally:
        conn.close()
    assert len(assigns) == 1 and assigns[0]["department"] == "Retail Banking"
    assert len(escs) == 1 and escs[0]["severity"] == "high"
