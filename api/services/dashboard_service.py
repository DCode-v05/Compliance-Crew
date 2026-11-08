"""Dashboard aggregation service.

Computes the command-center metrics from the persisted audit tables: counts of
controls, rejections, violations, escalations, the audit-chain integrity flag,
and department / risk load distributions. These are cross-run cumulative totals,
matching how a compliance team watches its programme over time."""

from __future__ import annotations

from pathlib import Path

from src.db import get_connection, list_runs, verify_audit_chain

CIRCULARS_DIR = Path("data/circulars")


def _scalar(conn, sql: str, default=0):
    row = conn.execute(sql).fetchone()
    if not row:
        return default
    val = row[0]
    return val if val is not None else default


def dashboard_stats() -> dict:
    conn = get_connection()
    try:
        total_runs = _scalar(conn, "SELECT COUNT(*) FROM pipeline_runs")
        controls_derived = _scalar(conn, "SELECT COUNT(*) FROM maps")
        controls_approved = _scalar(
            conn,
            "SELECT COUNT(DISTINCT map_id) FROM validations WHERE verdict = 'approved'",
        )
        validator_rejections = _scalar(
            conn, "SELECT COUNT(*) FROM validations WHERE verdict = 'rejected'"
        )
        total_violations = _scalar(
            conn, "SELECT COALESCE(SUM(violations_found), 0) FROM evidence_checks"
        )
        open_escalations = _scalar(conn, "SELECT COUNT(*) FROM escalations")
        audit_entries = _scalar(conn, "SELECT COUNT(*) FROM audit_entries")
        ev_total = _scalar(conn, "SELECT COUNT(*) FROM evidence_checks WHERE evaluated = 1")
        ev_compliant = _scalar(
            conn, "SELECT COUNT(*) FROM evidence_checks WHERE evaluated = 1 AND compliant = 1"
        )

        by_department = [
            {"department": r["department"], "count": r["n"]}
            for r in conn.execute(
                "SELECT department, COUNT(*) AS n FROM assignments "
                "GROUP BY department ORDER BY n DESC"
            )
        ]
        by_risk = [
            {"risk_category": r["risk_category"], "count": r["n"]}
            for r in conn.execute(
                "SELECT risk_category, COUNT(*) AS n FROM maps "
                "GROUP BY risk_category ORDER BY n DESC"
            )
        ]
    finally:
        conn.close()

    chain = verify_audit_chain()
    compliance_rate = round(ev_compliant / ev_total, 3) if ev_total else 0.0
    circulars_available = (
        len(list(CIRCULARS_DIR.glob("*.pdf")) + list(CIRCULARS_DIR.glob("*.txt")))
        if CIRCULARS_DIR.exists()
        else 0
    )

    recent = []
    for r in list_runs(limit=5):
        recent.append(
            {
                "run_id": r["run_id"],
                "circular": r["circular"],
                "source_doc_id": r["source_doc_id"],
                "classification": r["classification"],
                "urgency_score": r["urgency_score"],
                "paragraphs": r["paragraphs"],
                "total_maps": r["total_maps"],
                "approved": r["approved"],
                "rejected": r["rejected"],
                "violations": r["violations"],
                "escalations": r["escalations"],
                "created_at": r["created_at"],
                "status": "completed",
            }
        )

    return {
        "total_runs": total_runs,
        "circulars_available": circulars_available,
        "controls_derived": controls_derived,
        "controls_approved": controls_approved,
        "validator_rejections": validator_rejections,
        "total_violations": total_violations,
        "open_escalations": open_escalations,
        "audit_entries": audit_entries,
        "chain_intact": chain["intact"],
        "compliance_rate": compliance_rate,
        "by_department": by_department,
        "by_risk": by_risk,
        "recent_runs": recent,
    }
