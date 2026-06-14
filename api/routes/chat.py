"""Compliance Q&A chatbot route."""

from __future__ import annotations

from fastapi import APIRouter

from api.schemas import ChatRequest, ChatResponse
from api.services import chat_service as svc

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(req: ChatRequest):
    return svc.answer_question(req.question, req.run_id)
