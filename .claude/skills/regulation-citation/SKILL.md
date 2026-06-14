---
name: regulation-citation
description: Enforces verbatim citation requirements for every claim about an RBI regulation produced by any agent in the ComplianceCrew pipeline.
---

# Regulation Citation Skill

When generating any claim about an RBI regulation, the output MUST include:

1. `paragraph_id`: The exact section/paragraph reference (e.g., "kyc_master_direction_2016-3.1.4")
2. `verbatim_quote`: A direct quote from the source paragraph, <= 50 words. MUST be an exact substring of the source paragraph text (whitespace and case insensitive).
3. `confidence`: Float between 0.0 and 1.0 reflecting the agent's certainty.
4. `source_doc_id`: The circular ID this came from (e.g., "kyc_master_direction_2016").

If you cannot produce all four fields with a verbatim_quote that is genuinely a substring of the source text, do NOT generate the claim. Return:

```json
{"error": "insufficient_citation_evidence"}
```

## Why this matters

The Validator agent runs a hash check on every `verbatim_quote` field before invoking the LLM. Any quote that is not a substring of the source paragraph is auto-rejected with `rejection_category: "wrong_paragraph"`. Paraphrases will be caught. This is the structural safeguard against citation hallucination.

## Application

This skill applies whenever an agent prompt instructs the model to cite a regulation paragraph. It governs:

- `src/agents/mapper.py` — every MAP must carry a citation.
- `src/agents/validator.py` — every validation must include `cited_text` that is verbatim from the source.
- `src/agents/evidence_checker.py` — every evidence check cites the MAP it validates.
- `src/agents/auditor.py` — every finding in the final report cites both the MAP and the source paragraph.

## Verification logic (reference)

```python
# src/utils/citation_check.py
def verify_verbatim_quote(quote: str, source_text: str) -> bool:
    """Whitespace- and case-insensitive substring check."""
    import re
    norm = lambda s: re.sub(r"\s+", " ", s.strip().lower())
    return norm(quote) in norm(source_text)
```

If `verify_verbatim_quote()` returns False, the citation is hallucinated and the MAP must be rejected before semantic LLM validation runs.
