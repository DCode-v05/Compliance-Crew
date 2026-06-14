"""Compliance Q&A chatbot service.

Answers CCO questions grounded strictly in a completed run: its source circular,
derived controls, validations, assignments, evidence checks, and escalations.
Uses the same free-tier ``llm_call`` wrapper (Groq Llama 3.3 70B) and the same
citation discipline as the pipeline."""

from __future__ import annotations

import logging

from pydantic import BaseModel

from src.db import get_run
from src.llm import llm_call
from src.prompts.chatbot_prompt import (
    CHATBOT_SYSTEM_PROMPT,
    CHATBOT_USER_PROMPT_TEMPLATE,
)
from src.state import Citation, ComplianceState

from .pipeline_service import latest_run_id

logger = logging.getLogger(__name__)


class _ChatAnswer(BaseModel):
    answer: str
    citations: list[Citation] = []
    grounded: bool = True


def _circular_block(state: ComplianceState) -> str:
    m = state.circular_meta
    if not m:
        return f"Circular: {state.source_doc_id}"
    lines = [
        f"Title: {m.title}",
        f"Reference: {m.reference_number or 'n/a'}",
        f"Classification: {m.classification} (urgency {m.urgency_score:.0%})",
        f"Synopsis: {m.synopsis}",
        "",
        "Source paragraphs:",
    ]
    for p in state.paragraphs[:12]:
        lines.append(f"[{p.paragraph_id}] {p.text}")
    return "\n".join(lines)


def _controls_block(state: ComplianceState) -> str:
    approved = set(state.approved_map_ids)
    asg = {a.map_id: a for a in state.assignments}
    lines: list[str] = []
    for m in state.maps:
        if m.map_id not in approved:
            continue
        a = asg.get(m.map_id)
        dept = f" → {a.department} [{a.priority}, {a.deadline_days}d]" if a else ""
        lines.append(
            f"- {m.control_title} [{m.risk_category}]{dept}\n"
            f"  {m.control_description}\n"
            f"  cite [{m.citation.paragraph_id}]: \"{m.citation.verbatim_quote}\""
        )
    return "\n".join(lines) or "(no approved controls)"


def _evidence_block(state: ComplianceState) -> str:
    ev = {c.map_id: c for c in state.evidence_checks}
    title = {m.map_id: m.control_title for m in state.maps}
    lines: list[str] = []
    for map_id, c in ev.items():
        status = "COMPLIANT" if c.compliant else f"{c.violations_found} violations"
        lines.append(f"- {title.get(map_id, map_id)}: {status}")
    for e in state.escalations:
        lines.append(
            f"- ESCALATION ({e.severity}): {title.get(e.map_id, e.map_id)} — {e.reason}"
        )
    return "\n".join(lines) or "(no evidence checks or escalations)"


def answer_question(question: str, run_id: str | None = None) -> dict:
    rid = run_id or latest_run_id()
    if not rid:
        return {
            "answer": "No compliance run has been completed yet. Run the pipeline "
            "first, then ask about its findings.",
            "citations": [],
            "grounded": False,
            "run_id": None,
        }

    row = get_run(rid)
    if not row:
        return {
            "answer": f"Run {rid} was not found.",
            "citations": [],
            "grounded": False,
            "run_id": rid,
        }

    state = ComplianceState.model_validate_json(row["state_json"])
    user_prompt = CHATBOT_USER_PROMPT_TEMPLATE.format(
        circular_block=_circular_block(state),
        controls_block=_controls_block(state),
        evidence_block=_evidence_block(state),
        question=question,
    )

    try:
        result = llm_call(
            system_prompt=CHATBOT_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_schema=_ChatAnswer,
            agent_name="chatbot",
            temperature=0.2,
        )
    except Exception as e:  # noqa: BLE001
        logger.error("Chatbot LLM call failed: %s", e)
        return {
            "answer": "The assistant is temporarily unavailable (LLM call failed). "
            "Check that GROQ_API_KEY is set in .env.",
            "citations": [],
            "grounded": False,
            "run_id": rid,
        }

    return {
        "answer": result.answer,
        "citations": [c.model_dump() for c in result.citations],
        "grounded": result.grounded,
        "run_id": rid,
    }
