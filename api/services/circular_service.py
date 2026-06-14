"""Circular intelligence service.

Discovers the regulation files available under ``data/circulars/`` and derives
document-level intelligence for each (classification, urgency, reference number,
synopsis) using the same heuristic Monitor logic the Ingestor uses. Results are
cached in-process so repeatedly opening the Circulars page doesn't re-parse PDFs."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from src.agents.ingestor import build_circular_meta, ingest

logger = logging.getLogger(__name__)

CIRCULARS_DIR = Path("data/circulars")
_SUFFIXES = {".pdf", ".txt", ".md"}
MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # 15 MB

# doc_id -> dict cache (cleared on process restart).
_CACHE: dict[str, dict] = {}


def _safe_stem(filename: str) -> str:
    """Sanitise an uploaded filename's stem to a filesystem-safe slug."""
    stem = Path(filename).stem
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-")
    return (stem or "circular")[:80]


def save_uploaded_circular(filename: str, content: bytes) -> dict:
    """Persist an uploaded circular to data/circulars/, parse it, return its meta.

    Validates the extension and size, sanitises the filename, avoids clobbering
    existing files, and rejects documents from which no text can be extracted
    (e.g. scanned-image PDFs)."""
    suffix = Path(filename).suffix.lower()
    if suffix not in _SUFFIXES:
        raise ValueError(f"Unsupported file type '{suffix or '?'}'. Allowed: PDF, TXT, MD.")
    if not content:
        raise ValueError("The uploaded file is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError(f"File too large ({len(content) // (1024 * 1024)} MB). Max is 15 MB.")

    CIRCULARS_DIR.mkdir(parents=True, exist_ok=True)
    stem = _safe_stem(filename)
    dest = CIRCULARS_DIR / f"{stem}{suffix}"
    counter = 1
    while dest.exists():
        dest = CIRCULARS_DIR / f"{stem}-{counter}{suffix}"
        counter += 1

    dest.write_bytes(content)
    _CACHE.pop(dest.stem, None)

    meta = _meta_for_path(dest)
    if not meta or meta.get("paragraph_count", 0) == 0:
        dest.unlink(missing_ok=True)
        _CACHE.pop(dest.stem, None)
        raise ValueError(
            "No readable text could be extracted. If this is a scanned PDF, it "
            "needs OCR before upload."
        )
    return meta


def _meta_for_path(path: Path) -> dict | None:
    doc_id = path.stem
    if doc_id in _CACHE:
        return _CACHE[doc_id]
    try:
        paragraphs = ingest(str(path), doc_id)
        meta = build_circular_meta(doc_id, paragraphs)
    except Exception as e:  # noqa: BLE001
        logger.warning("Could not parse circular %s: %s", path, e)
        return None
    out = meta.model_dump()
    out["path"] = str(path).replace("\\", "/")
    _CACHE[doc_id] = out
    return out


def list_circulars() -> list[dict]:
    if not CIRCULARS_DIR.exists():
        return []
    items: list[dict] = []
    for path in sorted(CIRCULARS_DIR.iterdir()):
        if path.suffix.lower() in _SUFFIXES and path.stem.lower() != "readme":
            meta = _meta_for_path(path)
            if meta:
                items.append(meta)
    # Highest urgency first so the most pressing circular leads the view.
    items.sort(key=lambda x: x.get("urgency_score", 0), reverse=True)
    return items


def get_circular(source_doc_id: str) -> dict | None:
    if not CIRCULARS_DIR.exists():
        return None
    for path in CIRCULARS_DIR.iterdir():
        if path.suffix.lower() in _SUFFIXES and path.stem == source_doc_id:
            return _meta_for_path(path)
    return None
