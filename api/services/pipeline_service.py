"""Pipeline orchestration service.

Bridges the LangGraph pipeline (``src.graph``) to the API: runs it (streaming
or synchronous), joins each MAP with its validation / assignment / evidence into
a single flat row for the UI, and persists every run to ``pipeline_runs``.

Streaming uses a plain synchronous generator of Server-Sent-Event dicts; the
route wraps it in a StreamingResponse, which Starlette iterates in a threadpool
so the blocking LLM calls never stall the event loop."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from src.agents.ingestor import ingest
from src.db import get_run, init_db, list_runs, save_run, verify_audit_chain
from src.graph import build_graph
from src.state import ComplianceState


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_state(obj) -> ComplianceState:
    if isinstance(obj, ComplianceState):
        return obj
    return ComplianceState.model_validate(obj)


def build_map_rows(state: ComplianceState) -> list[dict]:
    """Join each MAP with its latest validation, assignment, and evidence check."""
    approved = set(state.approved_map_ids)
    escalated_ids = {e.map_id for e in state.escalations}

    val_by_map: dict[str, object] = {}
    for v in state.validations:
        val_by_map[v.map_id] = v
    asg_by_map = {a.map_id: a for a in state.assignments}
    ev_by_map = {c.map_id: c for c in state.evidence_checks}

    rows: list[dict] = []
    for m in state.maps:
        v = val_by_map.get(m.map_id)
        a = asg_by_map.get(m.map_id)
        ev = ev_by_map.get(m.map_id)
        verdict = (
            "approved"
            if m.map_id in approved
            else (v.verdict if v else "pending")
        )
        rows.append(
            {
                "map_id": m.map_id,
                "paragraph_id": m.paragraph_id,
                "control_title": m.control_title,
                "control_description": m.control_description,
                "evidence_type": m.evidence_type,
                "risk_category": m.risk_category,
                "attempt_number": m.attempt_number,
                "citation": m.citation.model_dump(),
                "verdict": verdict,
                "rejection_category": (v.rejection_category if v else None),
                "validation_reasoning": (v.reasoning if v else None),
                "cited_text": (v.cited_text if v else None),
                "department": (a.department if a else None),
                "priority": (a.priority if a else None),
                "deadline_days": (a.deadline_days if a else None),
                "dependencies": (a.dependencies if a else []),
                "evidence_compliant": (ev.compliant if ev else None),
                "evidence_evaluated": (ev.evaluated if ev else None),
                "violations_found": (ev.violations_found if ev else None),
                "sample_violation_ids": (ev.sample_violation_ids if ev else []),
                "escalated": m.map_id in escalated_ids,
            }
        )
    return rows


def summarize_state(
    state: ComplianceState, run_id: str, created_at: str
) -> dict:
    meta = state.circular_meta
    rejected = sum(1 for v in state.validations if v.verdict == "rejected")
    violations = sum(c.violations_found for c in state.evidence_checks)
    return {
        "run_id": run_id,
        "circular": Path(state.circular_pdf_path).name,
        "source_doc_id": state.source_doc_id,
        "classification": meta.classification if meta else "General",
        "urgency_score": meta.urgency_score if meta else 0.5,
        "paragraphs": len(state.paragraphs),
        "total_maps": len(state.maps),
        "approved": len(state.approved_map_ids),
        "rejected": rejected,
        "violations": violations,
        "escalations": len(state.escalations),
        "created_at": created_at,
        "status": "completed",
    }


def _persist(state: ComplianceState, run_id: str, created_at: str) -> dict:
    summary = summarize_state(state, run_id, created_at)
    save_run(summary, state.model_dump_json())
    return summary


def _prepare_initial(circular_path: str, max_paragraphs: int) -> ComplianceState:
    """Pre-ingest and cap paragraphs so a run stays fast and bounded."""
    init_db()
    doc_id = Path(circular_path).stem
    paragraphs = ingest(circular_path, doc_id)[:max_paragraphs]
    return ComplianceState(
        circular_pdf_path=circular_path,
        source_doc_id=doc_id,
        paragraphs=paragraphs,
    )


def run_sync(circular_path: str, max_paragraphs: int) -> dict:
    """Run the pipeline to completion and persist it. Returns a run summary."""
    initial = _prepare_initial(circular_path, max_paragraphs)
    if not initial.paragraphs:
        raise ValueError("No paragraphs were extracted from the source circular.")
    graph = build_graph()
    result = graph.invoke(initial, config={"recursion_limit": 50})
    state = _as_state(result)
    run_id = str(uuid.uuid4())
    return _persist(state, run_id, _now_iso())


def run_stream(circular_path: str, max_paragraphs: int) -> Iterator[dict]:
    """Yield SSE event dicts as the pipeline executes, then a terminal 'done'.

    Each yielded dict is ``{"event": <type>, "data": {...}}``. Types:
    ``agent`` (one streamed agent reasoning event), ``error``, ``done``."""
    try:
        initial = _prepare_initial(circular_path, max_paragraphs)
    except Exception as e:  # noqa: BLE001
        yield {"event": "error", "data": {"message": f"Ingestion failed: {e}"}}
        return

    if not initial.paragraphs:
        yield {"event": "error", "data": {"message": "No paragraphs extracted from source."}}
        return

    graph = build_graph()
    run_id = str(uuid.uuid4())
    created_at = _now_iso()
    sent = 0
    final_state: ComplianceState | None = None

    try:
        for chunk in graph.stream(initial, config={"recursion_limit": 50}):
            for _node, node_state in chunk.items():
                state = _as_state(node_state)
                final_state = state
                events = state.stream_events
                for ev in events[sent:]:
                    yield {"event": "agent", "data": ev}
                sent = len(events)
    except Exception as e:  # noqa: BLE001
        yield {"event": "error", "data": {"message": f"Pipeline failed: {e}"}}
        return

    if final_state is not None:
        summary = _persist(final_state, run_id, created_at)
        yield {"event": "done", "data": summary}
    else:
        yield {"event": "error", "data": {"message": "Pipeline produced no state."}}


def latest_run_id() -> str | None:
    runs = list_runs(limit=1)
    return runs[0]["run_id"] if runs else None


def get_run_detail(run_id: str) -> dict | None:
    row = get_run(run_id)
    if not row:
        return None
    state = ComplianceState.model_validate_json(row["state_json"])
    summary = summarize_state(state, run_id, row["created_at"])
    summary["maps"] = build_map_rows(state)
    summary["events"] = state.stream_events
    summary["report_markdown"] = state.final_report_markdown
    return summary


def maps_for_run(run_id: str | None) -> list[dict]:
    rid = run_id or latest_run_id()
    if not rid:
        return []
    row = get_run(rid)
    if not row:
        return []
    state = ComplianceState.model_validate_json(row["state_json"])
    return build_map_rows(state)


def _key_set(name: str) -> bool:
    """True only if the env var is set to a real value (not a placeholder)."""
    val = (os.getenv(name) or "").strip()
    return bool(val) and "your_" not in val and val.lower() != "changeme"


def llm_status() -> dict:
    groq = _key_set("GROQ_API_KEY")
    return {
        "provider": "groq",
        "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "configured": groq,
        "reachable": groq,
        "detail": (
            "Groq configured (free tier)."
            if groq
            else "GROQ_API_KEY missing — add it to .env to run the pipeline."
        ),
    }


def audit_chain_status() -> dict:
    return verify_audit_chain()


def sse_format(item: dict) -> str:
    """Render a {'event','data'} dict as a Server-Sent-Events frame."""
    event = item.get("event", "message")
    data = json.dumps(item.get("data", {}))
    return f"event: {event}\ndata: {data}\n\n"
