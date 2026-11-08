"""Validator node tests — the adversarial reviewer and its free hash check."""

from __future__ import annotations

from src.agents.validator import validator_node
from src.db import save_map
from src.state import MAP, Citation, ComplianceState, Paragraph, Validation

PARA_TEXT = (
    "Regulated Entities shall periodically update KYC records, in any case at "
    "least once in every two years for high risk customers."
)


def _state_with_pending_map(quote: str, paragraph_id: str = "kyc-3.1.4") -> ComplianceState:
    para = Paragraph(
        paragraph_id="kyc-3.1.4",
        section_title="t",
        text=PARA_TEXT,
        page_number=1,
        source_doc_id="kyc",
    )
    m = MAP(
        map_id="m1",
        paragraph_id=paragraph_id,
        control_title="t",
        control_description="d",
        evidence_type="customer_record",
        risk_category="high",
        citation=Citation(
            paragraph_id=paragraph_id,
            verbatim_quote=quote,
            confidence=0.9,
            source_doc_id="kyc",
        ),
    )
    s = ComplianceState(circular_pdf_path="x.pdf")
    s.paragraphs = [para]
    s.maps = [m]
    s.pending_map_ids = ["m1"]
    save_map(m)
    return s


def test_missing_paragraph_is_rejected(tmp_db):
    state = _state_with_pending_map("shall periodically update KYC records", paragraph_id="does-not-exist")
    out = validator_node(state)
    assert "m1" in out.rejected_map_ids
    assert out.validations[0].rejection_category == "wrong_paragraph"


def test_fabricated_quote_rejected_before_llm(tmp_db, monkeypatch):
    def boom(**kwargs):
        raise AssertionError("LLM should not be called for a fabricated quote")

    monkeypatch.setattr("src.agents.validator.llm_call", boom)
    state = _state_with_pending_map("shall annually update KYC for everyone")
    out = validator_node(state)
    assert "m1" in out.rejected_map_ids
    assert out.validations[0].rejection_category == "wrong_paragraph"


def test_valid_quote_approved_via_llm(tmp_db, monkeypatch):
    def fake_llm_call(**kwargs):
        return Validation(
            map_id="m1",
            verdict="approved",
            reasoning="Faithfully captures the tiered requirement.",
            cited_text="at least once in every two years for high risk customers",
            rejection_category="none",
        )

    monkeypatch.setattr("src.agents.validator.llm_call", fake_llm_call)
    state = _state_with_pending_map("shall periodically update KYC records")
    out = validator_node(state)
    assert "m1" in out.approved_map_ids
    assert out.rejected_map_ids == []
    assert out.pending_map_ids == []
