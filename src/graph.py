"""LangGraph wiring.

Five nodes, one conditional edge. The conditional edge from Validator back
to Mapper is the spine of the demo — every other piece of code serves it.

Flow:
    ingestor -> mapper -> validator -> [conditional]
                                          |--> mapper (if any rejection under retry cap)
                                          \\--> assigner (otherwise)
                  assigner -> evidence_checker -> auditor -> END
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from langgraph.graph import END, StateGraph

from src.agents.assigner import assigner_node
from src.agents.auditor import auditor_node
from src.agents.evidence_checker import evidence_node
from src.agents.ingestor import ingestor_node
from src.agents.mapper import mapper_node
from src.agents.validator import validator_node
from src.db import init_db
from src.state import ComplianceState

load_dotenv()

MAX_VALIDATION_RETRIES = 2


def route_after_validation(state: ComplianceState) -> str:
    """Conditional edge: retry Mapper for any rejected MAPs under the cap.

    A MAP's ``attempt_number`` tells us how many tries it has had. We retry
    a paragraph only if its highest attempt so far is below MAX_VALIDATION_RETRIES.
    """
    if not state.rejected_map_ids:
        return "assigner"

    rejected_maps = [m for m in state.maps if m.map_id in state.rejected_map_ids]
    if all(m.attempt_number >= MAX_VALIDATION_RETRIES for m in rejected_maps):
        # Retry cap reached for every rejected MAP — proceed with what we have
        return "assigner"

    return "mapper"


def build_graph():
    """Compile and return the LangGraph."""
    g = StateGraph(ComplianceState)

    g.add_node("ingestor", ingestor_node)
    g.add_node("mapper", mapper_node)
    g.add_node("validator", validator_node)
    g.add_node("assigner", assigner_node)
    g.add_node("evidence_checker", evidence_node)
    g.add_node("auditor", auditor_node)

    g.set_entry_point("ingestor")
    g.add_edge("ingestor", "mapper")
    g.add_edge("mapper", "validator")
    g.add_conditional_edges(
        "validator",
        route_after_validation,
        {"mapper": "mapper", "assigner": "assigner"},
    )
    g.add_edge("assigner", "evidence_checker")
    g.add_edge("evidence_checker", "auditor")
    g.add_edge("auditor", END)

    return g.compile()


def run_pipeline(
    pdf_path: str | Path,
    source_doc_id: str | None = None,
    bank_data_dir: str = "data/synthetic_bank",
) -> ComplianceState:
    """End-to-end pipeline runner. Used by ``__main__`` and the API."""
    init_db()
    initial = ComplianceState(
        circular_pdf_path=str(pdf_path),
        source_doc_id=source_doc_id or Path(pdf_path).stem,
        bank_data_dir=bank_data_dir,
    )
    graph = build_graph()
    # LangGraph returns either a dict or a state object depending on config.
    result = graph.invoke(initial, config={"recursion_limit": 50})
    if isinstance(result, dict):
        return ComplianceState.model_validate(result)
    return result


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        # Default to the sample paragraph file if no PDF is given
        sample = Path("data/circulars/sample_kyc_paragraph.txt")
        if not sample.exists():
            print(
                "Usage: python -m src.graph <pdf_path> [source_doc_id]\n"
                "Or place a PDF at data/circulars/ and a sample text file at "
                "data/circulars/sample_kyc_paragraph.txt"
            )
            sys.exit(1)
        pdf = str(sample)
    else:
        pdf = sys.argv[1]
    doc_id = sys.argv[2] if len(sys.argv) > 2 else Path(pdf).stem

    print(f"Running pipeline on {pdf}")
    final_state = run_pipeline(pdf, source_doc_id=doc_id)
    print(f"\nIngested:    {len(final_state.paragraphs)} paragraphs")
    print(f"MAPs:        {len(final_state.maps)} ({len(final_state.approved_map_ids)} approved)")
    print(f"Validations: {len(final_state.validations)}")
    print(f"  rejected:  {sum(1 for v in final_state.validations if v.verdict == 'rejected')}")
    print(f"  approved:  {sum(1 for v in final_state.validations if v.verdict == 'approved')}")
    print(f"Evidence checks: {len(final_state.evidence_checks)}")
    print(f"Violations:  {sum(c.violations_found for c in final_state.evidence_checks)}")
    print("\nReport written to data/output/final_report.md")
