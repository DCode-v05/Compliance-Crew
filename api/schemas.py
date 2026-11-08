"""Typed request/response models for the ComplianceCrew API.

These are the contract the Next.js frontend's ``lib/types.ts`` mirrors. Keeping
them in one place makes the API self-documenting via FastAPI's OpenAPI schema."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    circular_path: str = "data/circulars/sample_kyc_paragraphs.txt"
    max_paragraphs: int = Field(default=6, ge=1, le=30)


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=2)
    run_id: str | None = None


class CitationOut(BaseModel):
    paragraph_id: str = ""
    verbatim_quote: str = ""
    confidence: float = 0.0
    source_doc_id: str = ""


class MapOut(BaseModel):
    """A control with its validation, assignment, and evidence joined in."""

    map_id: str
    paragraph_id: str
    control_title: str
    control_description: str
    evidence_type: str
    risk_category: str
    attempt_number: int = 1
    citation: CitationOut | None = None
    verdict: str | None = None
    rejection_category: str | None = None
    validation_reasoning: str | None = None
    cited_text: str | None = None
    department: str | None = None
    priority: str | None = None
    deadline_days: int | None = None
    dependencies: list[str] = []
    evidence_compliant: bool | None = None
    evidence_evaluated: bool | None = None
    violations_found: int | None = None
    sample_violation_ids: list[str] = []
    escalated: bool = False


class RunSummary(BaseModel):
    run_id: str
    circular: str
    source_doc_id: str
    classification: str = "General"
    urgency_score: float = 0.5
    paragraphs: int = 0
    total_maps: int = 0
    approved: int = 0
    rejected: int = 0
    violations: int = 0
    escalations: int = 0
    created_at: str = ""
    status: str = "completed"


class StreamEvent(BaseModel):
    agent: str
    summary: str
    detail: str = ""


class RunDetail(RunSummary):
    maps: list[MapOut] = []
    events: list[StreamEvent] = []
    report_markdown: str = ""


class CircularOut(BaseModel):
    source_doc_id: str
    title: str = ""
    reference_number: str = ""
    classification: str = "General"
    urgency_score: float = 0.5
    effective_date: str = ""
    paragraph_count: int = 0
    synopsis: str = ""
    path: str = ""


class DepartmentLoad(BaseModel):
    department: str
    count: int


class RiskLoad(BaseModel):
    risk_category: str
    count: int


class DashboardStats(BaseModel):
    total_runs: int = 0
    circulars_available: int = 0
    controls_derived: int = 0
    controls_approved: int = 0
    validator_rejections: int = 0
    total_violations: int = 0
    open_escalations: int = 0
    audit_entries: int = 0
    chain_intact: bool = True
    compliance_rate: float = 0.0
    by_department: list[DepartmentLoad] = []
    by_risk: list[RiskLoad] = []
    recent_runs: list[RunSummary] = []


class ChatResponse(BaseModel):
    answer: str
    citations: list[CitationOut] = []
    grounded: bool = True
    run_id: str | None = None


class LlmStatus(BaseModel):
    provider: str = "groq"
    model: str = ""
    configured: bool = False
    reachable: bool = False
    detail: str = ""


class AuditChainStatus(BaseModel):
    intact: bool
    total: int
    broken_at: int | None = None
    detail: str
