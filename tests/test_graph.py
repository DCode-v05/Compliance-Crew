"""Graph construction and routing tests.

These tests verify the graph shape and the conditional edge logic WITHOUT
invoking the LLMs (which would need API keys and network)."""

from __future__ import annotations

from src.graph import MAX_VALIDATION_RETRIES, build_graph, route_after_validation
from src.state import MAP, Citation, ComplianceState


def _citation() -> Citation:
    return Citation(
        paragraph_id="p1",
        verbatim_quote="quote",
        confidence=0.9,
        source_doc_id="doc",
    )


def _map(map_id: str, attempt: int) -> MAP:
    return MAP(
        map_id=map_id,
        paragraph_id="p1",
        control_title="t",
        control_description="d",
        evidence_type="customer_record",
        risk_category="high",
        citation=_citation(),
        attempt_number=attempt,
    )


def test_graph_compiles():
    g = build_graph()
    # Smoke: graph has the six expected nodes plus an entry.
    nodes = set(g.get_graph().nodes.keys())
    for expected in {"ingestor", "mapper", "validator", "assigner", "evidence_checker", "auditor"}:
        assert expected in nodes


def test_route_proceeds_when_nothing_rejected():
    state = ComplianceState(circular_pdf_path="x.pdf")
    state.rejected_map_ids = []
    # On no rejections we advance to the Assigner (which precedes evidence check).
    assert route_after_validation(state) == "assigner"


def test_route_retries_when_under_cap():
    state = ComplianceState(circular_pdf_path="x.pdf")
    m = _map("m1", attempt=1)
    state.maps = [m]
    state.rejected_map_ids = ["m1"]
    # MAX_VALIDATION_RETRIES is at least 2, so attempt 1 should retry
    assert MAX_VALIDATION_RETRIES >= 2
    assert route_after_validation(state) == "mapper"


def test_route_proceeds_when_retry_cap_hit():
    state = ComplianceState(circular_pdf_path="x.pdf")
    m = _map("m1", attempt=MAX_VALIDATION_RETRIES)
    state.maps = [m]
    state.rejected_map_ids = ["m1"]
    # Cap reached: stop retrying and advance to the Assigner with what we have.
    assert route_after_validation(state) == "assigner"
