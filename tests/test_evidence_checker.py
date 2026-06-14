"""Evidence Checker tests — query execution and graceful failure handling.

The LLM is monkeypatched to return a fixed QueryPlan; the deterministic
DataFrame.query() execution is what we actually exercise."""

from __future__ import annotations

import pandas as pd
import pytest

from src.agents.evidence_checker import QueryPlan, evidence_node
from src.db import save_map
from src.state import MAP, Citation, ComplianceState, Paragraph


@pytest.fixture
def bank_dir(tmp_path):
    """A synthetic customers.csv with two high-risk KYC violations."""
    df = pd.DataFrame(
        [
            {"customer_id": "CUST-1", "risk_category": "high", "days_since_last_kyc": 900},
            {"customer_id": "CUST-2", "risk_category": "high", "days_since_last_kyc": 800},
            {"customer_id": "CUST-3", "risk_category": "high", "days_since_last_kyc": 100},
            {"customer_id": "CUST-4", "risk_category": "low", "days_since_last_kyc": 2000},
        ]
    )
    df.to_csv(tmp_path / "customers.csv", index=False)
    return str(tmp_path)


def _state_with_one_map(bank_data_dir: str) -> ComplianceState:
    para = Paragraph(
        paragraph_id="p1",
        section_title="t",
        text="High-risk customers must refresh KYC within two years.",
        page_number=1,
        source_doc_id="kyc",
    )
    m = MAP(
        map_id="m1",
        paragraph_id="p1",
        control_title="Periodic KYC",
        control_description="d",
        evidence_type="customer_record",
        risk_category="high",
        citation=Citation(paragraph_id="p1", verbatim_quote="q", confidence=0.9, source_doc_id="kyc"),
    )
    s = ComplianceState(circular_pdf_path="x.pdf", bank_data_dir=bank_data_dir)
    s.paragraphs = [para]
    s.maps = [m]
    s.approved_map_ids = ["m1"]
    # Persist the MAP so the evidence_checks FK (map_id -> maps) is satisfied.
    save_map(m)
    return s


def test_valid_query_counts_violations(tmp_db, monkeypatch, bank_dir):
    def fake_llm_call(**kwargs):
        return QueryPlan(
            dataset_name="customers",
            filter_expression="risk_category == 'high' and days_since_last_kyc > 730",
            columns_to_return=["customer_id"],
            reasoning="High-risk customers overdue for KYC refresh.",
        )

    monkeypatch.setattr("src.agents.evidence_checker.llm_call", fake_llm_call)
    out = evidence_node(_state_with_one_map(bank_dir))

    assert len(out.evidence_checks) == 1
    ev = out.evidence_checks[0]
    assert ev.evaluated is True
    assert ev.violations_found == 2
    assert ev.compliant is False
    assert set(ev.sample_violation_ids) == {"CUST-1", "CUST-2"}


def test_malformed_query_is_not_evaluated(tmp_db, monkeypatch, bank_dir):
    def fake_llm_call(**kwargs):
        return QueryPlan(
            dataset_name="customers",
            filter_expression="THIS IS NOT VALID PANDAS",
            columns_to_return=[],
            reasoning="r",
        )

    monkeypatch.setattr("src.agents.evidence_checker.llm_call", fake_llm_call)
    out = evidence_node(_state_with_one_map(bank_dir))

    assert len(out.evidence_checks) == 1
    ev = out.evidence_checks[0]
    # A failed query must NOT crash the pipeline, and must be recorded as
    # un-evaluated (not silently "compliant").
    assert ev.evaluated is False
    assert ev.compliant is False
    assert ev.violations_found == 0
    assert "not evaluated" in ev.reasoning.lower()
