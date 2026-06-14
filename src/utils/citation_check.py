"""Verbatim quote verification.

The 20 lines of code that make the demo bulletproof. Before the LLM Validator
runs, every MAP's ``citation.verbatim_quote`` is hash-checked against the
source paragraph. If the quote is not actually a substring (whitespace- and
case-insensitive), the MAP is auto-rejected with category ``wrong_paragraph``.

This catches the most catastrophic failure mode — fabricated citations —
without burning an LLM call."""

from __future__ import annotations

import re


def normalise(text: str) -> str:
    """Collapse whitespace, strip, lowercase. Used on both sides of the compare."""
    return re.sub(r"\s+", " ", text.strip().lower())


def verify_verbatim_quote(quote: str, source_text: str) -> bool:
    """True iff ``quote`` is a substring of ``source_text`` modulo whitespace/case.

    Whitespace-only or empty quotes are rejected even though the empty string
    is technically a substring of anything. The point of this check is to
    confirm a real citation exists, not to satisfy set-theoretic vacuity."""
    if not quote or not source_text:
        return False
    norm_quote = normalise(quote)
    if not norm_quote:
        return False
    return norm_quote in normalise(source_text)


if __name__ == "__main__":
    assert verify_verbatim_quote(
        "shall periodically update KYC",
        "Regulated Entities shall periodically update KYC records.",
    )
    assert verify_verbatim_quote(
        "Shall   periodically  update   KYC",
        "Regulated Entities shall periodically update KYC records.",
    )
    assert not verify_verbatim_quote(
        "shall annually update KYC",
        "Regulated Entities shall periodically update KYC records.",
    )
    assert not verify_verbatim_quote("", "anything")
    print("citation check tests passed")
