"""Auditor agent — assembles the final cited report.

One LLM call for the executive summary; everything else is deterministic
markdown templating. Output is written to ``data/output/final_report.md``
and also returned in state.final_report_markdown for the UI's Report tab."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel

from src.llm import llm_call
from src.prompts.auditor_prompt import (
    AUDITOR_SYSTEM_PROMPT,
    AUDITOR_USER_PROMPT_TEMPLATE,
)
from src.state import ComplianceState, EvidenceCheck, MAP

logger = logging.getLogger(__name__)

REPORT_PATH = Path("data/output/final_report.md")


class _ExecSummary(BaseModel):
    executive_summary: str


def _executive_summary(state: ComplianceState) -> str:
    total_paragraphs = len(state.paragraphs)
    approved_maps = [m for m in state.maps if m.map_id in state.approved_map_ids]
    total_maps = len(state.maps)
    approved_count = len(approved_maps)
    total_violations = sum(c.violations_found for c in state.evidence_checks)
    high_risk_count = sum(
        1
        for m in approved_maps
        if m.risk_category in {"high", "critical"}
        and any(
            c.map_id == m.map_id and c.violations_found > 0
            for c in state.evidence_checks
        )
    )

    top_findings_lines: list[str] = []
    for m in approved_maps[:5]:
        ev = next((c for c in state.evidence_checks if c.map_id == m.map_id), None)
        status = "compliant"
        if ev and not ev.compliant:
            status = f"{ev.violations_found} violations"
        top_findings_lines.append(f"- {m.control_title} [{m.risk_category}]: {status}")
    top_findings = "\n".join(top_findings_lines) or "- (none)"

    prompt = AUDITOR_USER_PROMPT_TEMPLATE.format(
        circular_name=Path(state.circular_pdf_path).name,
        total_paragraphs=total_paragraphs,
        total_maps=total_maps,
        approved_count=approved_count,
        total_violations=total_violations,
        high_risk_count=high_risk_count,
        top_findings=top_findings,
    )

    try:
        result = llm_call(
            system_prompt=AUDITOR_SYSTEM_PROMPT,
            user_prompt=prompt,
            response_schema=_ExecSummary,
            agent_name="auditor",
        )
        return result.executive_summary
    except Exception as e:
        logger.warning("Auditor executive-summary LLM call failed: %s", e)
        return (
            f"Analysed {total_paragraphs} paragraphs and derived {approved_count} "
            f"approved controls from {Path(state.circular_pdf_path).name}. "
            f"Total of {total_violations} compliance violations identified across "
            f"{high_risk_count} high-risk control(s) requiring remediation."
        )


def _render_finding(idx: int, m: MAP, ev: EvidenceCheck | None, page_lookup: dict[str, int]) -> str:
    page = page_lookup.get(m.paragraph_id, 0)
    status = "compliant"
    sample_block = ""
    if ev:
        if not ev.evaluated:
            status = "NOT EVALUATED"
        elif ev.compliant:
            status = "COMPLIANT"
        else:
            status = f"NON-COMPLIANT ({ev.violations_found} violations)"
            if ev.sample_violation_ids:
                sample_block = (
                    f"\n**Sample violations:** {', '.join(ev.sample_violation_ids[:10])}"
                )

    return f"""### Finding {idx}: {m.control_title}

**Control:** {m.control_description}
**Source:** {m.paragraph_id} (p.{page})
**Citation:** "{m.citation.verbatim_quote}"
**Evidence type:** {m.evidence_type}
**Risk:** {m.risk_category}
**Evidence status:** {status}{sample_block}

---
"""


def auditor_node(state: ComplianceState) -> ComplianceState:
    """Assemble the final markdown report."""
    approved_maps = [m for m in state.maps if m.map_id in state.approved_map_ids]
    page_lookup = {p.paragraph_id: p.page_number for p in state.paragraphs}
    ev_by_map = {c.map_id: c for c in state.evidence_checks}

    exec_summary = _executive_summary(state)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    findings_md = "\n".join(
        _render_finding(i + 1, m, ev_by_map.get(m.map_id), page_lookup)
        for i, m in enumerate(approved_maps)
    )

    total_violations = sum(c.violations_found for c in state.evidence_checks)
    rejection_count = sum(1 for v in state.validations if v.verdict == "rejected")

    report = f"""# Compliance Audit Report
**Circular:** {Path(state.circular_pdf_path).name}
**Date:** {now}
**Auditor:** ComplianceCrew v1.0

## Executive Summary
{exec_summary}

## Scope
- Paragraphs analysed: {len(state.paragraphs)}
- Controls derived (MAPs): {len(state.maps)}
- Controls approved by Validator: {len(approved_maps)}
- Validator rejections (caught before reaching evidence): {rejection_count}
- Total violations across sample bank data: {total_violations}

## Findings

{findings_md}

## Audit Trail
{len(state.maps) + len(state.validations) + len(state.evidence_checks)} agent
artefacts produced. Full trail available in `compliance.db` under tables
`audit_entries`, `maps`, `validations`, `evidence_checks`.
"""

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    state.final_report_markdown = report
    state.stream_events.append(
        {
            "agent": "auditor",
            "summary": f"Report compiled — {len(approved_maps)} findings, {total_violations} violations",
            "detail": f"Saved to {REPORT_PATH}",
        }
    )
    return state
