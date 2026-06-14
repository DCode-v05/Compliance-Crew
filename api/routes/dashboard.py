"""Dashboard stats route."""

from __future__ import annotations

from fastapi import APIRouter

from api.schemas import DashboardStats
from api.services import dashboard_service as svc

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def dashboard_stats():
    return svc.dashboard_stats()
