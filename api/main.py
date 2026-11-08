"""ComplianceCrew FastAPI application.

Wraps the LangGraph compliance pipeline in a typed REST + SSE API for the
Next.js frontend. Free-tier Groq Llama 3.3 70B — no Azure OpenAI.

Run:
    uvicorn api.main:app --reload --port 8000
Interactive docs at http://localhost:8000/docs
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import audit, chat, circulars, dashboard, health, maps, pipeline
from src.db import init_db

load_dotenv()

app = FastAPI(
    title="ComplianceCrew API",
    description=(
        "Five-agent RBI-circular compliance engine with cited reasoning, a "
        "tamper-proof SHA-256 audit chain, department routing, and a grounded "
        "compliance Q&A assistant. Powered by free-tier Groq Llama 3.3 70B."
    ),
    version="1.0.0",
)

_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
_extra = os.getenv("FRONTEND_ORIGIN")
if _extra:
    _origins.append(_extra)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()


app.include_router(health.router)
app.include_router(pipeline.router)
app.include_router(dashboard.router)
app.include_router(circulars.router)
app.include_router(maps.router)
app.include_router(chat.router)
app.include_router(audit.router)


@app.get("/")
def root():
    return {
        "service": "ComplianceCrew API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
