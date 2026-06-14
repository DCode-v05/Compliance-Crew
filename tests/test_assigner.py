"""Tests for the Assigner's deterministic logic (deadline clamp + fallback)."""

from __future__ import annotations

from src.agents.assigner import _DEADLINE_BOUNDS, _clamp_deadline, _fallback_assignment
from src.state import MAP, Citation


def _map(evidence_type="customer_record", risk="high") -> MAP:
    return MAP(
        map_id="m1",
        paragraph_id="p1",
        control_title="t",
        control_description="d",
        evidence_type=evidence_type,
        risk_category=risk,
        citation=Citation(paragraph_id="p1", verbatim_quote="q", confidence=0.9, source_doc_id="doc"),
    )


def test_clamp_keeps_within_bounds():
    lo, hi = _DEADLINE_BOUNDS["urgent"]
    assert _clamp_deadline("urgent", 1) == lo
    assert _clamp_deadline("urgent", 9999) == hi
    assert _clamp_deadline("urgent", (lo + hi) // 2) == (lo + hi) // 2


def test_fallback_routes_by_evidence_type():
    assert _fallback_assignment(_map("training_record", "low")).department == "HR/Training"
    assert _fallback_assignment(_map("system_config", "medium")).department == "IT/Digital"
    assert _fallback_assignment(_map("transaction_log", "high")).department == "Risk/AML"


def test_fallback_priority_tracks_risk():
    assert _fallback_assignment(_map(risk="critical")).priority == "critical"
    assert _fallback_assignment(_map(risk="low")).priority == "routine"


def test_fallback_deadline_within_bounds():
    a = _fallback_assignment(_map(risk="high"))
    lo, hi = _DEADLINE_BOUNDS[a.priority]
    assert lo <= a.deadline_days <= hi
