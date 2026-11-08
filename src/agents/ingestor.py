"""Ingestor agent.

Pure-Python paragraph extraction — no LLM call. Faster, deterministic, free.
The Ingestor splits a regulation PDF into paragraphs with stable IDs that
every downstream agent can cite back to.

Strategy:
1. Extract text page by page.
2. Detect numbered sections (e.g. "3.1.4", "38.", "(a)", "(i)").
3. Group consecutive lines under their nearest preceding section header.
4. Assign each paragraph an ID of the form ``{source_doc_id}-{section}``.

If section detection fails (unstructured PDF), fall back to fixed-size
chunking with synthetic IDs of the form ``{source_doc_id}-p{N}``."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from src.state import CircularMeta, ComplianceState, Paragraph
from src.utils.pdf_parser import extract_pages

logger = logging.getLogger(__name__)


_CLASSIFICATION_RULES: list[tuple[str, list[str]]] = [
    ("KYC/AML", ["kyc", "know your customer", "money laundering", "pmla", "cdd",
                 "suspicious transaction", "str", "ctr", "fiu"]),
    ("Cyber Security", ["cyber", "security incident", "data breach", "phishing",
                        "encryption", "vulnerability"]),
    ("Payments & Settlement", ["payment", "upi", "neft", "rtgs", "settlement",
                               "card", "wallet"]),
    ("Credit & Risk", ["credit risk", "npa", "provisioning", "exposure", "basel"]),
    ("Governance", ["board", "governance", "disclosure", "audit committee"]),
]

_URGENCY_TERMS = [
    "immediate", "with immediate effect", "within seven", "within 7",
    "shall report", "mandatory", "penalty", "non-compliance", "deadline",
    "forthwith", "no later than", "critical",
]

_REF_PATTERNS = [
    re.compile(r"\bRBI/\d{4}-\d{2}/\d+\b", re.IGNORECASE),
    re.compile(r"\b[A-Z]{2,4}\.[A-Z]{2,4}\.[A-Z]{1,3}\.No\.[\w./-]+", re.IGNORECASE),
    re.compile(r"\bDBR\.[\w./-]+", re.IGNORECASE),
]

_DATE_PATTERN = re.compile(
    r"\b(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+\d{4})\b",
    re.IGNORECASE,
)


def _has_term(low: str, term: str) -> bool:
    """Whole-word/phrase match so short acronyms (ctr, str, kyc) don't match
    inside unrelated words (e.g. 'ctr' inside 'electronic')."""
    return re.search(rf"\b{re.escape(term)}\b", low) is not None


def _classify(text: str) -> str:
    low = text.lower()
    for label, terms in _CLASSIFICATION_RULES:
        if any(_has_term(low, t) for t in terms):
            return label
    return "General"


def _urgency_score(text: str, paragraph_count: int) -> float:
    low = text.lower()
    hits = sum(1 for t in _URGENCY_TERMS if _has_term(low, t))
    score = 0.35 + min(hits, 6) * 0.08 + min(paragraph_count, 10) * 0.01
    return round(min(score, 0.99), 2)


def build_circular_meta(
    source_doc_id: str, paragraphs: list[Paragraph]
) -> CircularMeta:
    """Derive document-level intelligence (the Monitor role) from parsed text.

    Heuristic, deterministic, and LLM-free so it never adds latency or cost to
    ingestion. Produces classification, urgency, reference number, effective
    date, and a one-line synopsis for the dashboard and Circulars view."""
    full_text = "\n".join(p.text for p in paragraphs)
    first = paragraphs[0] if paragraphs else None

    reference_number = ""
    for pat in _REF_PATTERNS:
        m = pat.search(full_text)
        if m:
            reference_number = m.group(0)
            break

    date_match = _DATE_PATTERN.search(full_text)
    effective_date = date_match.group(1) if date_match else ""

    title = source_doc_id.replace("_", " ").replace("-", " ").title()
    if first and len(first.section_title) > 8:
        title = first.section_title[:90]

    synopsis = (first.text[:220] + "…") if first and len(first.text) > 220 else (
        first.text if first else ""
    )

    return CircularMeta(
        source_doc_id=source_doc_id,
        title=title,
        reference_number=reference_number,
        classification=_classify(full_text),
        urgency_score=_urgency_score(full_text, len(paragraphs)),
        effective_date=effective_date,
        paragraph_count=len(paragraphs),
        synopsis=synopsis,
    )


_SECTION_PATTERNS = [
    re.compile(r"^\s*(\d+(?:\.\d+){1,3})\.?\s+(.+)$"),
    re.compile(r"^\s*(\d{1,3})\.\s+(.+)$"),
    re.compile(r"^\s*\(([a-z]{1,3}|[ivx]{1,4})\)\s+(.+)$", re.IGNORECASE),
]

_MIN_PARAGRAPH_CHARS = 60


def _detect_section_header(line: str) -> tuple[str, str] | None:
    """Return (section_id, remainder) if line starts with a section marker."""
    for pat in _SECTION_PATTERNS:
        m = pat.match(line)
        if m:
            return m.group(1), m.group(2)
    return None


def ingest(pdf_path: str | Path, source_doc_id: str) -> list[Paragraph]:
    """Parse a PDF into structured paragraphs."""
    pages = extract_pages(pdf_path)
    paragraphs: list[Paragraph] = []

    current_section: str | None = None
    current_title: str = ""
    current_buf: list[str] = []
    current_page: int = 1

    def flush() -> None:
        if not current_section or not current_buf:
            return
        text = " ".join(current_buf).strip()
        if len(text) < _MIN_PARAGRAPH_CHARS:
            return
        paragraphs.append(
            Paragraph(
                paragraph_id=f"{source_doc_id}-{current_section}",
                section_title=current_title[:120] or current_section,
                text=text,
                page_number=current_page,
                source_doc_id=source_doc_id,
            )
        )

    for page_num, page_text in enumerate(pages, start=1):
        for raw_line in page_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            header = _detect_section_header(line)
            if header:
                flush()
                current_section, remainder = header
                current_title = remainder
                current_buf = [remainder]
                current_page = page_num
            elif current_section:
                current_buf.append(line)

    flush()

    if not paragraphs:
        logger.warning(
            "No structured paragraphs detected in %s — falling back to chunking",
            pdf_path,
        )
        paragraphs = _fallback_chunk(pages, source_doc_id)

    return paragraphs


def _fallback_chunk(pages: list[str], source_doc_id: str) -> list[Paragraph]:
    """Last-resort chunking for unstructured PDFs."""
    chunks: list[Paragraph] = []
    counter = 0
    for page_num, page_text in enumerate(pages, start=1):
        for block in re.split(r"\n\s*\n", page_text):
            block = block.strip()
            if len(block) < _MIN_PARAGRAPH_CHARS:
                continue
            counter += 1
            chunks.append(
                Paragraph(
                    paragraph_id=f"{source_doc_id}-p{counter}",
                    section_title=block[:80],
                    text=block,
                    page_number=page_num,
                    source_doc_id=source_doc_id,
                )
            )
    return chunks


def ingestor_node(state: ComplianceState) -> ComplianceState:
    """LangGraph node wrapper.

    Idempotent on paragraphs: if state already has them (e.g. the UI
    pre-ingested and capped them), we keep them. Circular metadata is computed
    here regardless, so the dashboard always has document-level intelligence.
    """
    if not state.paragraphs:
        paragraphs = ingest(state.circular_pdf_path, state.source_doc_id)
        state.paragraphs = paragraphs
        state.stream_events.append(
            {
                "agent": "ingestor",
                "summary": f"Parsed {len(paragraphs)} paragraphs from {Path(state.circular_pdf_path).name}",
                "detail": "",
            }
        )

    if state.circular_meta is None and state.paragraphs:
        meta = build_circular_meta(state.source_doc_id, state.paragraphs)
        state.circular_meta = meta
        state.stream_events.append(
            {
                "agent": "ingestor",
                "summary": (
                    f"Classified as {meta.classification} · "
                    f"urgency {meta.urgency_score:.0%}"
                ),
                "detail": (
                    f"{meta.reference_number or 'no ref. no.'} · "
                    f"{meta.paragraph_count} paragraphs"
                ),
            }
        )

    return state


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m src.agents.ingestor <pdf_path> [source_doc_id]")
        sys.exit(1)
    pdf = sys.argv[1]
    doc_id = sys.argv[2] if len(sys.argv) > 2 else Path(pdf).stem
    paras = ingest(pdf, doc_id)
    print(f"Extracted {len(paras)} paragraphs from {pdf}")
    for p in paras[:3]:
        print(f"\n--- {p.paragraph_id} (p.{p.page_number}) ---")
        print(p.text[:200])
