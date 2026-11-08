"""Shared Pydantic state passed between LangGraph nodes.

Every agent reads from and writes to ComplianceState. No untyped dicts cross
node boundaries. Citation is mandatory on every MAP and validation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Paragraph(BaseModel):
    """A single paragraph extracted from a regulation PDF."""

    paragraph_id: str
    section_title: str
    text: str
    page_number: int
    source_doc_id: str


class Citation(BaseModel):
    """Mandatory on every MAP and every Evidence check."""

    paragraph_id: str
    verbatim_quote: str = Field(..., max_length=500)
    confidence: float = Field(..., ge=0.0, le=1.0)
    source_doc_id: str


EvidenceType = Literal[
    "customer_record",
    "transaction_log",
    "policy_document",
    "audit_log",
    "training_record",
    "system_config",
]

RiskCategory = Literal["low", "medium", "high", "critical"]


class MAP(BaseModel):
    """Mapped Action Policy: a regulation paragraph translated into a control."""

    model_config = ConfigDict(populate_by_name=True)

    map_id: str = ""
    paragraph_id: str
    control_title: str
    control_description: str
    evidence_type: EvidenceType
    risk_category: RiskCategory
    citation: Citation
    created_at: datetime = Field(default_factory=_utcnow)
    attempt_number: int = 1


RejectionCategory = Literal[
    "hallucinated_requirement",
    "wrong_paragraph",
    "scope_mismatch",
    "insufficient_evidence",
    "none",
]


class Validation(BaseModel):
    """Validator's verdict on a MAP."""

    validation_id: str = ""
    map_id: str = ""
    verdict: Literal["approved", "rejected"]
    reasoning: str
    cited_text: str
    rejection_category: RejectionCategory = "none"
    created_at: datetime = Field(default_factory=_utcnow)


class EvidenceCheck(BaseModel):
    """Result of checking sample bank data against a single approved MAP."""

    check_id: str = ""
    map_id: str
    compliant: bool
    violations_found: int
    sample_violation_ids: list[str] = []
    reasoning: str
    citation: Citation
    evaluated: bool = True


Department = Literal[
    "IT/Digital",
    "Retail Banking",
    "Risk/AML",
    "HR/Training",
    "Legal/Compliance",
    "Operations",
]

AssignmentPriority = Literal["routine", "elevated", "urgent", "critical"]


class Assignment(BaseModel):
    """Assigner output: an approved control routed to a department with a
    deadline and any cross-control dependencies."""

    assignment_id: str = ""
    map_id: str
    department: Department
    priority: AssignmentPriority
    deadline_days: int = Field(..., ge=1, le=365)
    dependencies: list[str] = []
    rationale: str


class Escalation(BaseModel):
    """A finding routed to the Chief Compliance Officer for human review.

    Triggered by FAIL evidence checks, high/critical risk with violations, or
    low Validator confidence — mirrors the reference engine's CCO governance."""

    escalation_id: str = ""
    map_id: str
    severity: Literal["high", "critical"]
    reason: str
    deadline_days: int = Field(default=30, ge=1, le=365)


class CircularMeta(BaseModel):
    """Document-level intelligence about an ingested circular (Monitor role).

    Computed once per run: classification, urgency, and a one-line synopsis so
    the dashboard and Circulars view have something richer than a filename."""

    source_doc_id: str
    title: str = ""
    reference_number: str = ""
    classification: str = "General"
    urgency_score: float = Field(default=0.5, ge=0.0, le=1.0)
    effective_date: str = ""
    paragraph_count: int = 0
    synopsis: str = ""


class AuditEntry(BaseModel):
    """One row per agent invocation; persisted to SQLite."""

    entry_id: str
    agent_name: str
    input_hash: str
    output_json: str
    latency_ms: int
    tokens_used: int = 0
    provider: Literal["groq"] = "groq"
    timestamp: datetime = Field(default_factory=_utcnow)


class ComplianceState(BaseModel):
    """Shared state object passed between LangGraph nodes."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    circular_pdf_path: str
    source_doc_id: str = "kyc_master_direction_2016"
    bank_data_dir: str = "data/synthetic_bank"

    paragraphs: list[Paragraph] = []
    circular_meta: CircularMeta | None = None

    maps: list[MAP] = []

    validations: list[Validation] = []

    assignments: list[Assignment] = []
    escalations: list[Escalation] = []

    evidence_checks: list[EvidenceCheck] = []

    final_report_markdown: str = ""

    pending_map_ids: list[str] = []
    rejected_map_ids: list[str] = []
    approved_map_ids: list[str] = []

    stream_events: list[dict] = []


if __name__ == "__main__":
    sample = ComplianceState(circular_pdf_path="data/circulars/kyc_master_direction_2016.pdf")
    print(sample.model_dump_json(indent=2))
