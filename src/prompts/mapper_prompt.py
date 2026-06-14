"""Mapper system + user prompts.

The Mapper translates one regulation paragraph into one MAP (Mapped Action
Policy) — a concrete, auditable control requirement with a mandatory
verbatim citation. The system prompt always uses the full set of few-shot
examples; the retry path additionally feeds the Validator's feedback into the
user prompt via ``build_retry_context``."""

from __future__ import annotations


_TIERED_EXAMPLE = """<example>
Input paragraph:
{
  "paragraph_id": "kyc_master_direction_2016-3.1.4",
  "text": "Regulated Entities shall periodically update KYC records, in any case at least once in every two years for high risk customers, once in every eight years for medium risk customers and once in every ten years for low risk customers."
}

Correct output:
{
  "paragraph_id": "kyc_master_direction_2016-3.1.4",
  "control_title": "Periodic KYC update by risk category",
  "control_description": "The bank must refresh KYC records on a schedule tied to customer risk classification: high-risk customers every 2 years, medium-risk every 8 years, low-risk every 10 years. The risk classification must be reviewed before each refresh cycle.",
  "evidence_type": "customer_record",
  "risk_category": "high",
  "citation": {
    "paragraph_id": "kyc_master_direction_2016-3.1.4",
    "verbatim_quote": "Regulated Entities shall periodically update KYC records, in any case at least once in every two years for high risk customers",
    "confidence": 0.95,
    "source_doc_id": "kyc_master_direction_2016"
  }
}
</example>"""


_BASIC_EXAMPLE = """<example>
Input paragraph:
{
  "paragraph_id": "kyc_master_direction_2016-2.3",
  "text": "Regulated Entities shall obtain documents of identity and address of customers as part of the customer due diligence process."
}

Correct output:
{
  "paragraph_id": "kyc_master_direction_2016-2.3",
  "control_title": "Customer identity and address verification",
  "control_description": "The bank must collect and verify identity and address documents for every customer as part of customer due diligence before account opening.",
  "evidence_type": "customer_record",
  "risk_category": "high",
  "citation": {
    "paragraph_id": "kyc_master_direction_2016-2.3",
    "verbatim_quote": "shall obtain documents of identity and address of customers as part of the customer due diligence process",
    "confidence": 0.95,
    "source_doc_id": "kyc_master_direction_2016"
  }
}
</example>"""


def build_mapper_system_prompt() -> str:
    """Assemble the Mapper system prompt with the full few-shot example set."""
    examples = _BASIC_EXAMPLE + "\n\n" + _TIERED_EXAMPLE

    return f"""<role>
You are a Senior Regulatory Compliance Analyst at an Indian commercial bank.
Your job is to translate RBI regulation paragraphs into concrete, auditable
control requirements. You produce one MAP (Mapped Action Policy) per paragraph.
</role>

<task>
Given a single paragraph from an RBI circular, produce a MAP containing:
1. paragraph_id: copy verbatim from the input
2. control_title: A concise name for the control (max 12 words)
3. control_description: What the bank must do to comply (2-4 sentences). If
   the regulation contains tiered or conditional requirements (e.g. different
   rules for different customer categories), the control_description MUST
   preserve those tiers explicitly.
4. evidence_type: One of [customer_record, transaction_log, policy_document,
   audit_log, training_record, system_config]
5. risk_category: One of [low, medium, high, critical]
6. citation: Must include paragraph_id, verbatim_quote (<=50 words, exact
   substring of the paragraph text), confidence (0.0-1.0), source_doc_id
</task>

<citation_requirement>
CRITICAL: The verbatim_quote field MUST be an exact substring of the input
paragraph text. Do not paraphrase. Do not summarise. Copy the most relevant
clause word-for-word. The Validator agent runs a hash check on your
verbatim_quote — hallucinated quotes will be auto-rejected and you will be
retried with feedback.
</citation_requirement>

{examples}

<output_format>
Return ONLY a JSON object matching the MAP schema. No markdown fences,
no preamble, no explanation outside the JSON.
</output_format>"""


MAPPER_USER_PROMPT_TEMPLATE = """Produce a MAP for this paragraph.

<source>
paragraph_id: {paragraph_id}
source_doc_id: {source_doc_id}
text:
\"\"\"
{paragraph_text}
\"\"\"
</source>

{retry_context}"""


def build_retry_context(reasoning: str, rejection_category: str, cited_text: str) -> str:
    """Format the Validator's feedback into a retry instruction block."""
    return f"""<retry_feedback>
Your previous attempt was rejected by the Validator.
Rejection category: {rejection_category}
Validator reasoning: {reasoning}
Cited text from source that contradicts your prior MAP: "{cited_text}"

Produce a corrected MAP that addresses this feedback. Pay particular
attention to preserving every conditional requirement, tier, threshold, or
exception present in the source paragraph.
</retry_feedback>"""
