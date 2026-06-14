"""Health check route."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/api/v1/health")
def health():
    return {"status": "ok", "service": "compliancecrew-api"}
