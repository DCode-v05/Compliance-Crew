"""Validator agent — adversarial reviewer of MAPs.

For each pending MAP, the Validator:

1. Runs a deterministic hash check on the verbatim_quote field. If the quote
   is not a substring of the source paragraph, the MAP is auto-rejected
   with rejection_category="wrong_paragraph". No LLM call burned.

2. Otherwise invokes the LLM with a structured prompt that returns a
   Validation containing verdict, reasoning, cited_text, and rejection_category.

3. Routes approved MAPs into ``approved_map_ids`` and rejected MAPs into
   ``rejected_map_ids``. The graph's conditional edge consumes those lists."""

from __future__ import annotations

import logging
import uuid

from src.db import save_validation
from src.llm import llm_call
from src.prompts.validator_prompt import (
    VALIDATOR_SYSTEM_PROMPT,
    VALIDATOR_USER_PROMPT_TEMPLATE,
)
from src.state import ComplianceState, Validation
from src.utils.citation_check import verify_verbatim_quote

logger = logging.getLogger(__name__)


def validator_node(state: ComplianceState) -> ComplianceState:
    """Validate every pending MAP."""
    paragraph_lookup = {p.paragraph_id: p for p in state.paragraphs}
    pending_maps = [m for m in state.maps if m.map_id in state.pending_map_ids]

    new_validations: list[Validation] = []
    newly_approved: list[str] = []
    newly_rejected: list[str] = []

    for m in pending_maps:
        source_para = paragraph_lookup.get(m.paragraph_id)
        if source_para is None:
            v = Validation(
                validation_id=str(uuid.uuid4()),
                map_id=m.map_id,
                verdict="rejected",
                reasoning=f"No source paragraph found with id {m.paragraph_id}.",
                cited_text="",
                rejection_category="wrong_paragraph",
            )
            new_validations.append(v)
            newly_rejected.append(m.map_id)
            save_validation(v)
            continue

        # Pre-LLM hash check — catches hallucinated citations for free.
        if not verify_verbatim_quote(m.citation.verbatim_quote, source_para.text):
            v = Validation(
                validation_id=str(uuid.uuid4()),
                map_id=m.map_id,
                verdict="rejected",
                reasoning=(
                    "The MAP's verbatim_quote is not a substring of the source "
                    "paragraph. Hash check failed before LLM review."
                ),
                cited_text=source_para.text[:200],
                rejection_category="wrong_paragraph",
            )
            new_validations.append(v)
            newly_rejected.append(m.map_id)
            save_validation(v)
            state.stream_events.append(
                {
                    "agent": "validator",
                    "summary": f"REJECTED {m.map_id[:6]} — wrong_paragraph (hash check failed)",
                    "detail": v.reasoning,
                }
            )
            continue

        user_prompt = VALIDATOR_USER_PROMPT_TEMPLATE.format(
            paragraph_id=source_para.paragraph_id,
            paragraph_text=source_para.text,
            map_json=m.model_dump_json(indent=2),
        )
        try:
            v = llm_call(
                system_prompt=VALIDATOR_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                response_schema=Validation,
                agent_name="validator",
            )
        except Exception as e:
            logger.error("Validator LLM failed on MAP %s: %s", m.map_id, e)
            v = Validation(
                validation_id=str(uuid.uuid4()),
                map_id=m.map_id,
                verdict="rejected",
                reasoning=f"Validator LLM call failed: {e}. Conservative reject.",
                cited_text=source_para.text[:200],
                rejection_category="insufficient_evidence",
            )

        v.validation_id = str(uuid.uuid4())
        v.map_id = m.map_id
        new_validations.append(v)
        save_validation(v)

        if v.verdict == "approved":
            newly_approved.append(m.map_id)
            state.stream_events.append(
                {
                    "agent": "validator",
                    "summary": f"APPROVED {m.map_id[:6]}",
                    "detail": v.reasoning,
                }
            )
        else:
            newly_rejected.append(m.map_id)
            state.stream_events.append(
                {
                    "agent": "validator",
                    "summary": f"REJECTED {m.map_id[:6]} — {v.rejection_category}",
                    "detail": v.reasoning,
                }
            )

    state.validations.extend(new_validations)
    state.approved_map_ids.extend(newly_approved)
    state.rejected_map_ids = newly_rejected
    state.pending_map_ids = []
    return state
