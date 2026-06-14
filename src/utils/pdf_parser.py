"""Lightweight PDF text extraction.

Uses pypdf as the primary path, with pdfplumber as a fallback for PDFs where
pypdf fails to extract clean text (scans, complex layouts). Both libraries
are pure Python — no system dependencies."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_pages(pdf_path: str | Path) -> list[str]:
    """Return a list of page texts. Index 0 is page 1.

    Accepts .pdf and .txt. A text file is treated as a single-page document.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if path.suffix.lower() in {".txt", ".md"}:
        return [path.read_text(encoding="utf-8")]

    pages: list[str] = []
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        if any(p.strip() for p in pages):
            return pages
        logger.info("pypdf returned empty pages — falling back to pdfplumber")
    except Exception as e:
        logger.warning("pypdf failed (%s); falling back to pdfplumber", e)

    try:
        import pdfplumber

        with pdfplumber.open(str(path)) as pdf:
            pages = [p.extract_text() or "" for p in pdf.pages]
    except Exception as e:
        raise RuntimeError(f"Both PDF parsers failed on {path}: {e}") from e

    return pages
