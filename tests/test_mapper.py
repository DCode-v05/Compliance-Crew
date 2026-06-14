"""Mapper agent tests.

The Mapper's most important behaviour to verify *without* the LLM:
1. Retry context is built from the Validator's last rejection.
2. The system prompt always carries the full few-shot example set.
3. The node assigns a fresh map_id and pins the paragraph_id to the source."""

from __future__ import annotations

from src.agents.mapper import mapper_node
from src.prompts.mapper_prompt import (
    build_mapper_system_prompt,
    build_retry_context,
)
from src.state import MAP, Citation, ComplianceState, Paragraph, Validation


def test_system_prompt_includes_full_example_set():
    prompt = build_mapper_system_prompt()
    # Both the basic and the tiered KYC few-shot examples are always present.
    assert "every two years" in prompt  # tiered example
    assert "identity and address" in prompt  # basic example
    assert "verbatim_quote" in prompt


def test_build_retry_context_contains_validator_feedback():
    ctx = build_retry_context(
        reasoning="You collapsed a tiered requirement into a flat one.",
        rejection_category="scope_mismatch",
        cited_text="every two years for high risk customers",
    )
    assert "scope_mismatch" in ctx
    assert "tiered requirement" in ctx
    assert "every two years for high risk customers" in ctx


def _make_state_with_rejection() -> ComplianceState:
    citation = Citation(
        paragraph_id="kyc-3.1.4",
        verbatim_quote="shall periodically update KYC records",
        confidence=0.9,
        source_doc_id="kyc",
    )
    rejected_map = MAP(
        map_id="bad-map",
        paragraph_id="kyc-3.1.4",
        control_title="wrong control",
        control_description="annual update for everyone",
        evidence_type="customer_record",
        risk_category="high",
        citation=citation,
        attempt_number=1,
    )
    rejection = Validation(
        validation_id="v1",
        map_id="bad-map",
        verdict="rejected",
        reasoning="scope mismatch — ignored tiering",
        cited_text="every two years for high risk customers",
        rejection_category="scope_mismatch",
    )
    p = Paragraph(
        paragraph_id="kyc-3.1.4",
        section_title="t",
        text="Regulated Entities shall periodically update KYC records, in any "
        "case at least once in every two years for high risk customers.",
        page_number=12,
        source_doc_id="kyc",
    )
    s = ComplianceState(circular_pdf_path="x.pdf")
    s.paragraphs = [p]
    s.maps = [rejected_map]
    s.validations = [rejection]
    s.rejected_map_ids = ["bad-map"]
    return s


def test_mapper_passes_retry_feedback_into_user_prompt(monkeypatch, tmp_db):
    """The Mapper must wire the prior rejection into the user prompt."""
    state = _make_state_with_rejection()

    captured = {}

    def fake_llm_call(**kwargs):
        captured["user_prompt"] = kwargs["user_prompt"]
        captured["system_prompt"] = kwargs["system_prompt"]
        return MAP(
            map_id="",
            paragraph_id="kyc-3.1.4",
            control_title="Risk-tiered KYC update",
            control_description=(
                "High-risk every 2 years, medium-risk every 8 years, "
                "low-risk every 10 years."
            ),
            evidence_type="customer_record",
            risk_category="high",
            citation=Citation(
                paragraph_id="kyc-3.1.4",
                verbatim_quote="shall periodically update KYC records",
                confidence=0.95,
                source_doc_id="kyc",
            ),
            attempt_number=1,  # will be overwritten by node
        )

    monkeypatch.setattr("src.agents.mapper.llm_call", fake_llm_call)

    out = mapper_node(state)

    assert "retry_feedback" in captured["user_prompt"]
    assert "scope_mismatch" in captured["user_prompt"]
    assert "every two years for high risk customers" in captured["user_prompt"]

    # The new MAP should be attempt #2 with a fresh UUID.
    assert len(out.maps) == 2
    new_map = out.maps[-1]
    assert new_map.attempt_number == 2
    assert new_map.map_id != "bad-map"
    assert new_map.paragraph_id == "kyc-3.1.4"
    assert out.pending_map_ids == [new_map.map_id]
