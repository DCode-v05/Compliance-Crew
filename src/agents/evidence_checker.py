"""Evidence Checker agent — runs an LLM-generated query against bank data.

The LLM returns a structured QueryPlan (which dataset, which filter
expression, which columns). The Python side deterministically loads the
appropriate CSV and runs ``DataFrame.query()`` on it. The LLM never
executes code; it only proposes a plan we validate.

This keeps the demo reliable: the worst failure mode is a malformed query
expression, which we catch with a try/except and record as a zero-violation
check with an explanatory reasoning."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field

from src.db import save_evidence_check
from src.llm import llm_call
from src.prompts.evidence_prompt import (
    EVIDENCE_SYSTEM_PROMPT,
    EVIDENCE_USER_PROMPT_TEMPLATE,
)
from src.state import ComplianceState, EvidenceCheck

logger = logging.getLogger(__name__)

MAX_VIOLATION_SAMPLES = 25


class QueryPlan(BaseModel):
    """The Evidence Checker's intermediate structured output."""

    dataset_name: Literal["customers", "transactions"]
    filter_expression: str = Field(..., min_length=1)
    columns_to_return: list[str] = []
    reasoning: str


def _load_dataset(bank_data_dir: str, dataset_name: str) -> pd.DataFrame:
    path = Path(bank_data_dir) / f"{dataset_name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    return pd.read_csv(path)


def _primary_key(dataset_name: str) -> str:
    return "customer_id" if dataset_name == "customers" else "transaction_id"


def evidence_node(state: ComplianceState) -> ComplianceState:
    """For every approved MAP, generate a query plan and execute it."""
    approved_maps = [m for m in state.maps if m.map_id in state.approved_map_ids]
    paragraph_lookup = {p.paragraph_id: p for p in state.paragraphs}
    dataset_cache: dict[str, pd.DataFrame] = {}

    for m in approved_maps:
        if any(c.map_id == m.map_id for c in state.evidence_checks):
            continue  # already checked this MAP

        para = paragraph_lookup.get(m.paragraph_id)
        para_text = para.text if para else ""

        user_prompt = EVIDENCE_USER_PROMPT_TEMPLATE.format(
            map_json=m.model_dump_json(indent=2),
            paragraph_text=para_text,
        )

        try:
            plan = llm_call(
                system_prompt=EVIDENCE_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                response_schema=QueryPlan,
                agent_name="evidence_checker",
            )
        except Exception as e:
            logger.error("Evidence query-plan failed for MAP %s: %s", m.map_id, e)
            check = EvidenceCheck(
                check_id=str(uuid.uuid4()),
                map_id=m.map_id,
                compliant=False,
                violations_found=0,
                sample_violation_ids=[],
                reasoning=f"Not evaluated — could not generate a query plan: {e}",
                citation=m.citation,
                evaluated=False,
            )
            state.evidence_checks.append(check)
            save_evidence_check(check)
            continue

        # Execute the query against the dataset
        try:
            if plan.dataset_name not in dataset_cache:
                dataset_cache[plan.dataset_name] = _load_dataset(
                    state.bank_data_dir, plan.dataset_name
                )
            df = dataset_cache[plan.dataset_name]
            violations = df.query(plan.filter_expression, engine="python")
        except Exception as e:
            logger.warning(
                "Query failed for MAP %s [%s]: %s",
                m.map_id,
                plan.filter_expression,
                e,
            )
            check = EvidenceCheck(
                check_id=str(uuid.uuid4()),
                map_id=m.map_id,
                compliant=False,
                violations_found=0,
                sample_violation_ids=[],
                reasoning=(
                    f"Not evaluated — query failed against {plan.dataset_name}: "
                    f"{plan.filter_expression!r}. Error: {e}"
                ),
                citation=m.citation,
                evaluated=False,
            )
            state.evidence_checks.append(check)
            save_evidence_check(check)
            continue

        pk = _primary_key(plan.dataset_name)
        sample_ids = (
            violations[pk].head(MAX_VIOLATION_SAMPLES).astype(str).tolist()
            if pk in violations.columns
            else []
        )
        violations_found = int(len(violations))
        check = EvidenceCheck(
            check_id=str(uuid.uuid4()),
            map_id=m.map_id,
            compliant=violations_found == 0,
            violations_found=violations_found,
            sample_violation_ids=sample_ids,
            reasoning=(
                f"{plan.reasoning} Query: `{plan.filter_expression}` on "
                f"{plan.dataset_name} ({len(df)} rows scanned) found "
                f"{violations_found} violating rows."
            ),
            citation=m.citation,
        )
        state.evidence_checks.append(check)
        save_evidence_check(check)

        state.stream_events.append(
            {
                "agent": "evidence_checker",
                "summary": (
                    f"{'COMPLIANT' if check.compliant else f'{violations_found} VIOLATIONS'} "
                    f"for MAP {m.map_id[:6]}"
                ),
                "detail": check.reasoning,
            }
        )

    return state
