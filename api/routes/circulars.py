"""Circular intelligence routes."""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from api.schemas import CircularOut
from api.services import circular_service as svc

router = APIRouter(prefix="/api/v1/circulars", tags=["circulars"])


@router.get("", response_model=list[CircularOut])
def list_circulars():
    return svc.list_circulars()


@router.post("/upload", response_model=CircularOut)
async def upload_circular(file: UploadFile = File(...)):
    """Upload a PDF/TXT/MD circular, store it, parse it, and return its intelligence."""
    content = await file.read()
    try:
        return svc.save_uploaded_circular(file.filename or "circular", content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}") from e


@router.get("/{source_doc_id}", response_model=CircularOut)
def get_circular(source_doc_id: str):
    meta = svc.get_circular(source_doc_id)
    if not meta:
        raise HTTPException(status_code=404, detail=f"Circular {source_doc_id} not found")
    return meta
