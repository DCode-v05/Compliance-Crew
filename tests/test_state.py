"""Pydantic state model tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.state import (
    MAP,
    Assignment,
    Citation,
    ComplianceState,
    EvidenceCheck,
    Paragraph,
    Validation,
)


def _citation() -> Citation:
    return Citation(
        paragraph_id="p1",
        verbatim_quote="shall do the thing",
        confidence=0.9,
        source_doc_id="doc",
    )


def test_citation_confidence_bounds():
    # confidence must be within 0..1
    with pytest.raises(ValidationError):
        Citation(paragraph_id="p", verbatim_quote="q", confidence=1.5, source_doc_id="d")
    with pytest.raises(ValidationError):
        Citation(paragraph_id="p", verbatim_quote="q", confidence=-0.1, source_doc_id="d")


def test_map_defaults():
    m = MAP(
        paragraph_id="p1",
        control_title="t",
        control_description="d",
        evidence_type="customer_record",
        risk_category="high",
        citation=_citation(),
    )
    assert m.map_id == ""
    assert m.attempt_number == 1


def test_evidence_check_evaluated_defaults_true():
    ev = EvidenceCheck(
        map_id="m1",
        compliant=True,
        violations_found=0,
        reasoning="ok",
        citation=_citation(),
    )
    assert ev.evaluated is True


def test_assignment_deadline_bounds():
    with pytest.raises(ValidationError):
        Assignment(
            map_id="m1",
            department="Retail Banking",
            priority="urgent",
            deadline_days=0,  # below ge=1
            rationale="r",
        )


def test_compliance_state_defaults():
    s = ComplianceState(circular_pdf_path="x.pdf")
    assert s.paragraphs == []
    assert s.maps == []
    assert s.assignments == []
    assert s.escalations == []
    assert s.circular_meta is None
    assert s.bank_data_dir == "data/synthetic_bank"


def test_state_roundtrip_json():
    s = ComplianceState(circular_pdf_path="x.pdf")
    s.paragraphs = [
        Paragraph(
            paragraph_id="p1",
            section_title="t",
            text="some text",
            page_number=1,
            source_doc_id="doc",
        )
    ]
    s.validations = [
        Validation(
            map_id="m1",
            verdict="approved",
            reasoning="ok",
            cited_text="some text",
        )
    ]
    dumped = s.model_dump_json()
    restored = ComplianceState.model_validate_json(dumped)
    assert restored.circular_pdf_path == "x.pdf"
    assert len(restored.paragraphs) == 1
    assert restored.validations[0].verdict == "approved"
