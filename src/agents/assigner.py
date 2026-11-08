"""Assigner agent — approved control -> department + deadline + dependencies.

Runs after the Validator. For every approved MAP it produces an Assignment
routing the control to a bank department with an implementation priority and
deadline, and records cross-control dependencies. It also raises an Escalation
to the CCO for any control that is high/critical risk — mirroring the reference
engine's "agents propose, humans approve consequential decisions" governance.

The LLM proposes routing; the agent clamps deadlines into policy bounds and
guarantees a valid department so downstream views never see a malformed plan."""

from __future__ import annotations

import logging
import uuid

from src.db import save_assignment, save_escalation
from src.llm import llm_call
from src.prompts.assigner_prompt import (
    ASSIGNER_SYSTEM_PROMPT,
    ASSIGNER_USER_PROMPT_TEMPLATE,
)
from src.state import Assignment, ComplianceState, Escalation, MAP

logger = logging.getLogger(__name__)

_DEADLINE_BOUNDS = {
    "critical": (7, 21),
    "urgent": (14, 45),
    "elevated": (30, 75),
    "routine": (60, 120),
}

_RISK_TO_PRIORITY = {
    "critical": "critical",
    "high": "urgent",
    "medium": "elevated",
    "low": "routine",
}

_EVIDENCE_TO_DEPT = {
    "customer_record": "Retail Banking",
    "transaction_log": "Risk/AML",
    "policy_document": "Legal/Compliance",
    "audit_log": "Operations",
    "training_record": "HR/Training",
    "system_config": "IT/Digital",
}


def _clamp_deadline(priority: str, deadline_days: int) -> int:
    lo, hi = _DEADLINE_BOUNDS.get(priority, (30, 90))
    return max(lo, min(hi, deadline_days))


def _fallback_assignment(m: MAP) -> Assignment:
    priority = _RISK_TO_PRIORITY.get(m.risk_category, "elevated")
    lo, hi = _DEADLINE_BOUNDS[priority]
    return Assignment(
        assignment_id=str(uuid.uuid4()),
        map_id=m.map_id,
        department=_EVIDENCE_TO_DEPT.get(m.evidence_type, "Operations"),  # type: ignore[arg-type]
        priority=priority,  # type: ignore[arg-type]
        deadline_days=hi,
        dependencies=[],
        rationale=(
            f"Deterministic routing by evidence type ({m.evidence_type}) and "
            f"risk ({m.risk_category}); LLM routing unavailable."
        ),
    )


def assigner_node(state: ComplianceState) -> ComplianceState:
    """Assign every approved MAP to a department and raise CCO escalations."""
    approved_maps = [m for m in state.maps if m.map_id in state.approved_map_ids]
    already_assigned = {a.map_id for a in state.assignments}
    valid_peer_ids = {m.map_id for m in approved_maps}

    peer_lines = "\n".join(
        f"- {m.map_id}: {m.control_title}" for m in approved_maps
    ) or "- (none)"

    new_assignments: list[Assignment] = []
    new_escalations: list[Escalation] = []

    for m in approved_maps:
        if m.map_id in already_assigned:
            continue

        user_prompt = ASSIGNER_USER_PROMPT_TEMPLATE.format(
            map_json=m.model_dump_json(indent=2),
            peer_controls=peer_lines,
        )
        try:
            assignment = llm_call(
                system_prompt=ASSIGNER_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                response_schema=Assignment,
                agent_name="assigner",
            )
        except Exception as e:
            logger.error("Assigner failed on MAP %s: %s", m.map_id, e)
            assignment = _fallback_assignment(m)

        assignment.assignment_id = str(uuid.uuid4())
        assignment.map_id = m.map_id
        assignment.deadline_days = _clamp_deadline(
            assignment.priority, assignment.deadline_days
        )
        assignment.dependencies = [
            d for d in assignment.dependencies if d in valid_peer_ids and d != m.map_id
        ]

        new_assignments.append(assignment)
        save_assignment(assignment)

        state.stream_events.append(
            {
                "agent": "assigner",
                "summary": (
                    f"MAP {m.map_id[:6]} -> {assignment.department} "
                    f"[{assignment.priority}, {assignment.deadline_days}d]"
                ),
                "detail": assignment.rationale,
            }
        )

        if m.risk_category in {"high", "critical"}:
            severity = "critical" if m.risk_category == "critical" else "high"
            esc = Escalation(
                escalation_id=str(uuid.uuid4()),
                map_id=m.map_id,
                severity=severity,  # type: ignore[arg-type]
                reason=(
                    f"{m.risk_category.title()}-risk control '{m.control_title}' "
                    f"routed to {assignment.department}; flagged for CCO sign-off."
                ),
                deadline_days=assignment.deadline_days,
            )
            new_escalations.append(esc)
            save_escalation(esc)
            state.stream_events.append(
                {
                    "agent": "assigner",
                    "summary": f"ESCALATED {m.map_id[:6]} to CCO — {severity} risk",
                    "detail": esc.reason,
                }
            )

    state.assignments.extend(new_assignments)
    state.escalations.extend(new_escalations)
    return state
