"""Mapper agent — paragraph -> MAP.

For each paragraph that does not yet have an approved MAP, generate a fresh
attempt. If the paragraph has prior rejections, feed the Validator's
feedback into the prompt so the retry is corrective, not blind."""

from __future__ import annotations

import logging
import uuid

from src.db import save_map
from src.llm import llm_call
from src.prompts.mapper_prompt import (
    MAPPER_USER_PROMPT_TEMPLATE,
    build_mapper_system_prompt,
    build_retry_context,
)
from src.state import MAP, ComplianceState

logger = logging.getLogger(__name__)


def _approved_paragraph_ids(state: ComplianceState) -> set[str]:
    approved_ids = set(state.approved_map_ids)
    return {m.paragraph_id for m in state.maps if m.map_id in approved_ids}


def _prior_rejections_for(state: ComplianceState, paragraph_id: str):
    """Validations rejecting any MAP for this paragraph, oldest first."""
    rejected_map_ids = {
        m.map_id for m in state.maps if m.paragraph_id == paragraph_id
    }
    return [
        v
        for v in state.validations
        if v.verdict == "rejected" and v.map_id in rejected_map_ids
    ]


def mapper_node(state: ComplianceState) -> ComplianceState:
    """Generate MAPs for every paragraph without an approved control yet."""
    approved = _approved_paragraph_ids(state)

    new_maps: list[MAP] = []
    for para in state.paragraphs:
        if para.paragraph_id in approved:
            continue

        prior = _prior_rejections_for(state, para.paragraph_id)
        is_retry = bool(prior)
        attempt = len(prior) + 1

        retry_context = ""
        if prior:
            last = prior[-1]
            retry_context = build_retry_context(
                reasoning=last.reasoning,
                rejection_category=last.rejection_category,
                cited_text=last.cited_text,
            )

        system_prompt = build_mapper_system_prompt()
        user_prompt = MAPPER_USER_PROMPT_TEMPLATE.format(
            paragraph_id=para.paragraph_id,
            source_doc_id=para.source_doc_id,
            paragraph_text=para.text,
            retry_context=retry_context,
        )

        try:
            result = llm_call(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_schema=MAP,
                agent_name="mapper",
            )
        except Exception as e:
            logger.error("Mapper failed on %s: %s", para.paragraph_id, e)
            continue

        result.map_id = str(uuid.uuid4())
        result.attempt_number = attempt
        result.paragraph_id = para.paragraph_id
        result.citation.paragraph_id = para.paragraph_id
        result.citation.source_doc_id = para.source_doc_id

        new_maps.append(result)
        save_map(result)

        verdict_word = "retry" if is_retry else "draft"
        state.stream_events.append(
            {
                "agent": "mapper",
                "summary": f"MAP {result.map_id[:6]} ({verdict_word} #{attempt}): \"{result.control_title}\"",
                "detail": result.citation.verbatim_quote,
            }
        )

    state.maps.extend(new_maps)
    state.pending_map_ids = [m.map_id for m in new_maps]
    return state
