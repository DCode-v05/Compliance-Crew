"""SQLite-backed audit trail with a tamper-proof hash chain.

The audit table is a feature, not a debug log. Judges and regulators will
scroll through it during Q&A. Every LLM call and every domain object written
to state is persisted here so the trail survives across runs.

Each ``audit_entries`` row is chained with SHA-256 (see ``src.utils.audit_chain``):
``entry_hash = sha256(prev_hash || payload)``. Editing any historical row breaks
every subsequent hash, which ``verify_audit_chain`` detects."""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from src.state import Assignment, EvidenceCheck, Escalation, MAP, Validation
from src.utils.audit_chain import (
    GENESIS_HASH,
    canonical_payload,
    compute_entry_hash,
    verify_chain,
)

DB_PATH = Path("compliance.db")

_lock = threading.Lock()


SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_entries (
    entry_id TEXT PRIMARY KEY,
    agent_name TEXT NOT NULL,
    input_hash TEXT NOT NULL,
    output_json TEXT NOT NULL,
    latency_ms INTEGER NOT NULL,
    tokens_used INTEGER DEFAULT 0,
    provider TEXT NOT NULL,
    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    prev_hash TEXT NOT NULL DEFAULT '',
    entry_hash TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_audit_agent ON audit_entries(agent_name);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_entries(timestamp);

CREATE TABLE IF NOT EXISTS maps (
    map_id TEXT PRIMARY KEY,
    paragraph_id TEXT NOT NULL,
    control_title TEXT NOT NULL,
    control_description TEXT NOT NULL,
    evidence_type TEXT NOT NULL,
    risk_category TEXT NOT NULL,
    citation_json TEXT NOT NULL,
    attempt_number INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS validations (
    validation_id TEXT PRIMARY KEY,
    map_id TEXT NOT NULL,
    verdict TEXT NOT NULL,
    reasoning TEXT NOT NULL,
    cited_text TEXT NOT NULL,
    rejection_category TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (map_id) REFERENCES maps(map_id)
);

CREATE TABLE IF NOT EXISTS evidence_checks (
    check_id TEXT PRIMARY KEY,
    map_id TEXT NOT NULL,
    compliant INTEGER NOT NULL,
    violations_found INTEGER NOT NULL,
    sample_violation_ids TEXT NOT NULL,
    reasoning TEXT NOT NULL,
    citation_json TEXT NOT NULL,
    evaluated INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (map_id) REFERENCES maps(map_id)
);

CREATE TABLE IF NOT EXISTS assignments (
    assignment_id TEXT PRIMARY KEY,
    map_id TEXT NOT NULL,
    department TEXT NOT NULL,
    priority TEXT NOT NULL,
    deadline_days INTEGER NOT NULL,
    dependencies TEXT NOT NULL DEFAULT '[]',
    rationale TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (map_id) REFERENCES maps(map_id)
);

CREATE TABLE IF NOT EXISTS escalations (
    escalation_id TEXT PRIMARY KEY,
    map_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    reason TEXT NOT NULL,
    deadline_days INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (map_id) REFERENCES maps(map_id)
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id TEXT PRIMARY KEY,
    circular TEXT NOT NULL,
    source_doc_id TEXT NOT NULL,
    classification TEXT NOT NULL DEFAULT 'General',
    urgency_score REAL NOT NULL DEFAULT 0.5,
    paragraphs INTEGER NOT NULL DEFAULT 0,
    total_maps INTEGER NOT NULL DEFAULT 0,
    approved INTEGER NOT NULL DEFAULT 0,
    rejected INTEGER NOT NULL DEFAULT 0,
    violations INTEGER NOT NULL DEFAULT 0,
    escalations INTEGER NOT NULL DEFAULT 0,
    state_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_runs_created ON pipeline_runs(created_at);
"""


def _resolve_db_path(db_path: Path | str | None) -> Path | str:
    """Resolve the db_path argument at call time so monkeypatches of
    ``src.db.DB_PATH`` are honoured. Binding ``DB_PATH`` directly as the
    default argument freezes it at module import time, defeating fixtures."""
    return db_path if db_path is not None else DB_PATH


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Open a SQLite connection with foreign keys enabled."""
    conn = sqlite3.connect(str(_resolve_db_path(db_path)), check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    """Additive migrations for databases created before the hash chain existed.

    SQLite's ``CREATE TABLE IF NOT EXISTS`` never alters an existing table, so
    we add the hash-chain columns by hand if a legacy ``audit_entries`` table
    is missing them. Safe to run on every init."""
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(audit_entries)")}
    if cols and "prev_hash" not in cols:
        conn.execute("ALTER TABLE audit_entries ADD COLUMN prev_hash TEXT NOT NULL DEFAULT ''")
    if cols and "entry_hash" not in cols:
        conn.execute("ALTER TABLE audit_entries ADD COLUMN entry_hash TEXT NOT NULL DEFAULT ''")
    ev_cols = {row["name"] for row in conn.execute("PRAGMA table_info(evidence_checks)")}
    if ev_cols and "evaluated" not in ev_cols:
        conn.execute("ALTER TABLE evidence_checks ADD COLUMN evaluated INTEGER NOT NULL DEFAULT 1")


def init_db(db_path: Path | str | None = None) -> None:
    """Create tables (and run additive migrations) if they don't exist."""
    with _lock:
        conn = get_connection(_resolve_db_path(db_path))
        try:
            conn.executescript(SCHEMA)
            _migrate(conn)
            conn.commit()
        finally:
            conn.close()


def reset_db(db_path: Path | str | None = None) -> None:
    """Delete the database file and recreate it. Used by seed_db.py."""
    p = Path(_resolve_db_path(db_path))
    if p.exists():
        p.unlink()
    init_db(p)


def log_audit_entry(
    agent_name: str,
    input_hash: str,
    output_json: str,
    latency_ms: int,
    tokens_used: int,
    provider: Literal["groq"] = "groq",
    db_path: Path | str | None = None,
) -> str:
    """Insert one audit row, extending the SHA-256 hash chain.

    Reads the most recent row's ``entry_hash`` as ``prev_hash`` (GENESIS for the
    first row), then stores ``entry_hash = sha256(prev_hash || payload)``.
    Returns the generated entry_id."""
    entry_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    with _lock:
        conn = get_connection(_resolve_db_path(db_path))
        try:
            row = conn.execute(
                "SELECT entry_hash FROM audit_entries ORDER BY rowid DESC LIMIT 1"
            ).fetchone()
            prev_hash = (row["entry_hash"] if row and row["entry_hash"] else GENESIS_HASH)
            payload = canonical_payload(
                entry_id=entry_id,
                agent_name=agent_name,
                input_hash=input_hash,
                output_json=output_json,
                latency_ms=latency_ms,
                provider=provider,
                timestamp=timestamp,
            )
            entry_hash = compute_entry_hash(prev_hash, payload)
            conn.execute(
                """
                INSERT INTO audit_entries
                  (entry_id, agent_name, input_hash, output_json,
                   latency_ms, tokens_used, provider, timestamp,
                   prev_hash, entry_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry_id,
                    agent_name,
                    input_hash,
                    output_json,
                    latency_ms,
                    tokens_used,
                    provider,
                    timestamp,
                    prev_hash,
                    entry_hash,
                ),
            )
            conn.commit()
        finally:
            conn.close()
    return entry_id


def verify_audit_chain(db_path: Path | str | None = None) -> dict:
    """Recompute the full hash chain from the DB and report whether it is intact."""
    conn = get_connection(_resolve_db_path(db_path))
    try:
        rows = [
            dict(r)
            for r in conn.execute(
                "SELECT entry_id, agent_name, input_hash, output_json, latency_ms, "
                "provider, timestamp, prev_hash, entry_hash "
                "FROM audit_entries ORDER BY rowid ASC"
            )
        ]
    finally:
        conn.close()
    return verify_chain(rows).as_dict()


def save_map(m: MAP, db_path: Path | str | None = None) -> None:
    with _lock:
        conn = get_connection(_resolve_db_path(db_path))
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO maps
                  (map_id, paragraph_id, control_title, control_description,
                   evidence_type, risk_category, citation_json,
                   attempt_number, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    m.map_id,
                    m.paragraph_id,
                    m.control_title,
                    m.control_description,
                    m.evidence_type,
                    m.risk_category,
                    m.citation.model_dump_json(),
                    m.attempt_number,
                    m.created_at.isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()


def save_validation(v: Validation, db_path: Path | str | None = None) -> None:
    with _lock:
        conn = get_connection(_resolve_db_path(db_path))
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO validations
                  (validation_id, map_id, verdict, reasoning,
                   cited_text, rejection_category, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    v.validation_id,
                    v.map_id,
                    v.verdict,
                    v.reasoning,
                    v.cited_text,
                    v.rejection_category,
                    v.created_at.isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()


def save_evidence_check(e: EvidenceCheck, db_path: Path | str | None = None) -> None:
    with _lock:
        conn = get_connection(_resolve_db_path(db_path))
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO evidence_checks
                  (check_id, map_id, compliant, violations_found,
                   sample_violation_ids, reasoning, citation_json, evaluated, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    e.check_id,
                    e.map_id,
                    int(e.compliant),
                    e.violations_found,
                    json.dumps(e.sample_violation_ids),
                    e.reasoning,
                    e.citation.model_dump_json(),
                    int(e.evaluated),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()


def save_assignment(a: Assignment, db_path: Path | str | None = None) -> None:
    with _lock:
        conn = get_connection(_resolve_db_path(db_path))
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO assignments
                  (assignment_id, map_id, department, priority,
                   deadline_days, dependencies, rationale, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    a.assignment_id,
                    a.map_id,
                    a.department,
                    a.priority,
                    a.deadline_days,
                    json.dumps(a.dependencies),
                    a.rationale,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()


def save_escalation(e: Escalation, db_path: Path | str | None = None) -> None:
    with _lock:
        conn = get_connection(_resolve_db_path(db_path))
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO escalations
                  (escalation_id, map_id, severity, reason, deadline_days, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    e.escalation_id,
                    e.map_id,
                    e.severity,
                    e.reason,
                    e.deadline_days,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()


def save_run(summary: dict, state_json: str, db_path: Path | str | None = None) -> None:
    """Persist a completed pipeline run (summary columns + full state JSON)."""
    with _lock:
        conn = get_connection(_resolve_db_path(db_path))
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO pipeline_runs
                  (run_id, circular, source_doc_id, classification, urgency_score,
                   paragraphs, total_maps, approved, rejected, violations,
                   escalations, state_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    summary["run_id"],
                    summary["circular"],
                    summary["source_doc_id"],
                    summary["classification"],
                    summary["urgency_score"],
                    summary["paragraphs"],
                    summary["total_maps"],
                    summary["approved"],
                    summary["rejected"],
                    summary["violations"],
                    summary["escalations"],
                    state_json,
                    summary["created_at"],
                ),
            )
            conn.commit()
        finally:
            conn.close()


def list_runs(limit: int = 50, db_path: Path | str | None = None) -> list[dict]:
    """Return run summaries, newest first (without the heavy state_json)."""
    conn = get_connection(_resolve_db_path(db_path))
    try:
        rows = conn.execute(
            "SELECT run_id, circular, source_doc_id, classification, urgency_score, "
            "paragraphs, total_maps, approved, rejected, violations, escalations, "
            "created_at FROM pipeline_runs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_run(run_id: str, db_path: Path | str | None = None) -> dict | None:
    """Return a single run including its full state_json, or None."""
    conn = get_connection(_resolve_db_path(db_path))
    try:
        row = conn.execute(
            "SELECT * FROM pipeline_runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Initialised database at {DB_PATH.absolute()}")
