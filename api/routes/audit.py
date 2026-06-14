"""Audit-trail routes — raw entries and hash-chain verification."""

from __future__ import annotations

from fastapi import APIRouter, Query

from api.schemas import AuditChainStatus
from api.services import pipeline_service as svc
from src.db import get_connection

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("/entries")
def audit_entries(limit: int = Query(500, ge=1, le=2000)):
    """Recent audit entries (newest first), including their chain hashes."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT entry_id, agent_name, provider, latency_ms, tokens_used, "
            "timestamp, input_hash, prev_hash, entry_hash "
            "FROM audit_entries ORDER BY rowid DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.get("/chain", response_model=AuditChainStatus)
def audit_chain():
    """Recompute and verify the SHA-256 audit hash chain end-to-end."""
    return svc.audit_chain_status()
