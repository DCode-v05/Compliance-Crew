"""Tamper-proof audit logging via a SHA-256 hash chain.

Every audit row stores ``prev_hash`` (the hash of the row before it) and
``entry_hash = sha256(prev_hash + canonical_payload)``. Because each hash
folds in the previous one, altering any historical row breaks every hash that
follows it — the chain is verifiable end-to-end and any tampering is detectable.

This is the cryptographic spine of the "RBI-ready, inspection-grade" audit
trail: a regulator can re-run ``verify_chain`` and confirm nothing was edited
after the fact.

The hashing here is pure and deterministic; persistence lives in ``src.db``."""

from __future__ import annotations

from hashlib import sha256
from typing import Iterable

GENESIS_HASH = "0" * 64


def canonical_payload(
    entry_id: str,
    agent_name: str,
    input_hash: str,
    output_json: str,
    latency_ms: int,
    provider: str,
    timestamp: str,
) -> str:
    """Deterministic string form of an audit row's signed fields.

    Field order is fixed and ``\\x1f`` (unit separator) delimited so the same
    logical row always hashes identically regardless of how it is stored.
    """
    parts = [
        entry_id,
        agent_name,
        input_hash,
        output_json,
        str(latency_ms),
        provider,
        timestamp,
    ]
    return "\x1f".join(parts)


def compute_entry_hash(prev_hash: str, payload: str) -> str:
    """Hash a row into the chain: sha256(prev_hash || payload)."""
    return sha256(f"{prev_hash}\x1e{payload}".encode("utf-8")).hexdigest()


class ChainVerification:
    """Result of verifying an audit chain."""

    def __init__(self, intact: bool, total: int, broken_at: int | None, detail: str):
        self.intact = intact
        self.total = total
        self.broken_at = broken_at
        self.detail = detail

    def as_dict(self) -> dict:
        return {
            "intact": self.intact,
            "total": self.total,
            "broken_at": self.broken_at,
            "detail": self.detail,
        }


def verify_chain(rows: Iterable[dict]) -> ChainVerification:
    """Walk an ordered iterable of audit rows and recompute the hash chain.

    Each row must expose: entry_id, agent_name, input_hash, output_json,
    latency_ms, provider, timestamp, prev_hash, entry_hash. Returns a
    ``ChainVerification`` describing whether the chain is intact and, if not,
    the 1-based index of the first row whose stored hash disagrees with the
    recomputed value.
    """
    rows = list(rows)
    expected_prev = GENESIS_HASH
    for idx, row in enumerate(rows, start=1):
        payload = canonical_payload(
            entry_id=row["entry_id"],
            agent_name=row["agent_name"],
            input_hash=row["input_hash"],
            output_json=row["output_json"],
            latency_ms=int(row["latency_ms"]),
            provider=row["provider"],
            timestamp=row["timestamp"],
        )
        if row.get("prev_hash") != expected_prev:
            return ChainVerification(
                intact=False,
                total=len(rows),
                broken_at=idx,
                detail=f"Row {idx} prev_hash does not match the prior entry_hash.",
            )
        recomputed = compute_entry_hash(expected_prev, payload)
        if recomputed != row.get("entry_hash"):
            return ChainVerification(
                intact=False,
                total=len(rows),
                broken_at=idx,
                detail=f"Row {idx} entry_hash does not match recomputed hash (row was altered).",
            )
        expected_prev = recomputed

    return ChainVerification(
        intact=True,
        total=len(rows),
        broken_at=None,
        detail=f"All {len(rows)} audit entries verified; hash chain intact.",
    )
