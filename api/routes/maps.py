"""MAP (control) routes — controls joined with validation, assignment, evidence."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from api.schemas import MapOut
from api.services import pipeline_service as svc

router = APIRouter(prefix="/api/v1/maps", tags=["maps"])


@router.get("", response_model=list[MapOut])
def list_maps(run_id: str | None = Query(None, description="Defaults to latest run")):
    return svc.maps_for_run(run_id)


@router.get("/{map_id}", response_model=MapOut)
def get_map(map_id: str, run_id: str | None = Query(None)):
    rows = svc.maps_for_run(run_id)
    for row in rows:
        if row["map_id"] == map_id:
            return row
    raise HTTPException(status_code=404, detail=f"MAP {map_id} not found")
