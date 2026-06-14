"""Pipeline routes: run (sync + SSE stream), list/get runs, report, LLM status."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from api.schemas import LlmStatus, RunDetail, RunRequest, RunSummary
from api.services import pipeline_service as svc
from src.db import list_runs

router = APIRouter(prefix="/api/v1/pipeline", tags=["pipeline"])


@router.post("/run", response_model=RunSummary)
def run_pipeline(req: RunRequest):
    """Run the full pipeline to completion (blocking) and return its summary."""
    try:
        return svc.run_sync(req.circular_path, req.max_paragraphs)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/stream")
def stream_pipeline(
    circular_path: str = Query("data/circulars/sample_kyc_paragraphs.txt"),
    max_paragraphs: int = Query(6, ge=1, le=30),
):
    """Server-Sent-Events stream of live agent reasoning, then a 'done' summary.

    GET (not POST) so the browser's native EventSource can consume it directly.
    """

    def gen():
        for item in svc.run_stream(circular_path, max_paragraphs):
            yield svc.sse_format(item)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/runs", response_model=list[RunSummary])
def get_runs(limit: int = Query(50, ge=1, le=200)):
    rows = list_runs(limit=limit)
    return [
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
        for r in rows
    ]


@router.get("/runs/{run_id}", response_model=RunDetail)
def get_run_detail(run_id: str):
    detail = svc.get_run_detail(run_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return detail


@router.get("/runs/{run_id}/report")
def get_run_report(run_id: str):
    detail = svc.get_run_detail(run_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return {"run_id": run_id, "report_markdown": detail.get("report_markdown", "")}


@router.get("/llm/status", response_model=LlmStatus)
def llm_status():
    return svc.llm_status()
