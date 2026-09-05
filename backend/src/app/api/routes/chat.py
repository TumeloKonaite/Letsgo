"""Serve complete and streaming chat replies, translating service failures to HTTP."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.schemas.chat import ChatRequest, ChatResponse
from app.chatbot.llm import LLMConfigurationError
from app.chatbot.service import TwinService
from app.core.dependencies import get_twin_service

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)

CHAT_UNAVAILABLE_DETAIL = "Chat service is unavailable."
CHAT_FAILURE_DETAIL = "Chat request failed."


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    twin_service: Annotated[TwinService, Depends(get_twin_service)],
) -> ChatResponse:
    try:
        result = twin_service.chat(request.message, request.session_id)
        return ChatResponse(response=result.response, session_id=result.session_id)
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=503, detail=CHAT_UNAVAILABLE_DETAIL) from exc
    except Exception as exc:
        logger.exception("Chat request failed.")
        raise HTTPException(status_code=500, detail=CHAT_FAILURE_DETAIL) from exc


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    twin_service: Annotated[TwinService, Depends(get_twin_service)],
):
    try:
        result = twin_service.stream_chat(request.message, request.session_id)
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=503, detail=CHAT_UNAVAILABLE_DETAIL) from exc
    except Exception as exc:
        logger.exception("Streaming chat request failed.")
        raise HTTPException(status_code=500, detail=CHAT_FAILURE_DETAIL) from exc

    return StreamingResponse(
        result.stream,
        media_type="text/plain; charset=utf-8",
        headers={"X-Session-Id": result.session_id},
    )


@router.get("/sessions")
async def list_sessions(
    twin_service: Annotated[TwinService, Depends(get_twin_service)],
) -> dict[str, list[dict[str, object]]]:
    return {"sessions": twin_service.list_sessions()}
