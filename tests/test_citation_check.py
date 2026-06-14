"""Citation verification tests — the structural anti-hallucination safeguard."""

from __future__ import annotations

from src.utils.citation_check import normalise, verify_verbatim_quote

SOURCE = "Regulated Entities shall periodically update KYC records."


def test_exact_substring_passes():
    assert verify_verbatim_quote("shall periodically update KYC", SOURCE)


def test_whitespace_and_case_insensitive():
    assert verify_verbatim_quote("Shall   periodically  update   KYC", SOURCE)
    assert verify_verbatim_quote("SHALL PERIODICALLY UPDATE KYC", SOURCE)


def test_paraphrase_is_rejected():
    assert not verify_verbatim_quote("shall annually update KYC", SOURCE)


def test_empty_or_whitespace_quote_rejected():
    assert not verify_verbatim_quote("", "anything")
    assert not verify_verbatim_quote("   ", SOURCE)
    assert not verify_verbatim_quote("real quote", "")


def test_normalise_collapses_whitespace():
    assert normalise("  Hello   World  ") == "hello world"
