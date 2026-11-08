"""Ingestor tests — section detection, parsing, and circular intelligence."""

from __future__ import annotations

from pathlib import Path

from src.agents.ingestor import (
    _classify,
    _detect_section_header,
    build_circular_meta,
    ingest,
)

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "circulars" / "sample_kyc_paragraphs.txt"


def test_detect_section_header_numbered():
    assert _detect_section_header("3.1.4 Periodic Updation of KYC") == ("3.1.4", "Periodic Updation of KYC")
    assert _detect_section_header("38. Top level paragraph text")[0] == "38"


def test_detect_section_header_subclause():
    res = _detect_section_header("(a) some lettered clause")
    assert res is not None and res[0] == "a"


def test_detect_section_header_none_for_plain_line():
    assert _detect_section_header("This is just a normal sentence.") is None


def test_ingest_sample_produces_cited_paragraphs():
    paras = ingest(str(SAMPLE), "kyc")
    assert len(paras) >= 5
    assert all(p.source_doc_id == "kyc" for p in paras)
    ids = {p.paragraph_id for p in paras}
    assert any(pid.endswith("-3.1.4") for pid in ids)


def test_build_circular_meta_classifies_kyc():
    paras = ingest(str(SAMPLE), "kyc")
    meta = build_circular_meta("kyc", paras)
    assert meta.classification == "KYC/AML"
    assert meta.paragraph_count == len(paras)
    assert 0.0 <= meta.urgency_score <= 1.0


def test_classify_uses_word_boundaries():
    assert _classify("electronic payment systems and settlement") != "KYC/AML"
    assert _classify("cyber security incident reporting") == "Cyber Security"
    assert _classify("KYC and money laundering controls") == "KYC/AML"
