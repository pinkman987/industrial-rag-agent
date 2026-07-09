import json
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.db import crud
from app.db.session import get_db
from app.rag.qa import answer_question
from app.schemas.rag import AskRequest, AskResponse, ChatHistoryItem, ChatHistoryResponse


router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/ask", response_model=AskResponse)
def ask_question(payload: AskRequest, db=Depends(get_db)):
    try:
        result = answer_question(payload.question)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    session_id = payload.session_id or str(uuid4())
    device = None
    message = result["message"]

    if payload.device_code:
        device = crud.get_device_by_code(db, payload.device_code)
        if device is None:
            message = f"{message} 提示：未找到设备编码 {payload.device_code}，本次对话未关联具体设备。"

    crud.save_chat_record(
        db,
        session_id=session_id,
        question=payload.question,
        answer=result["answer"],
        sources=result["sources"],
        device_id=device.id if device else None,
    )

    return AskResponse(
        message=message,
        answer=result["answer"],
        sources=result["sources"],
        session_id=session_id,
    )


def _decode_sources(sources_json: Optional[str]) -> list:
    if not sources_json:
        return []
    try:
        sources = json.loads(sources_json)
    except json.JSONDecodeError:
        return []
    return sources if isinstance(sources, list) else []


def _decode_tool_calls(tool_calls_json: Optional[str]) -> list:
    if not tool_calls_json:
        return []
    try:
        tool_calls = json.loads(tool_calls_json)
    except json.JSONDecodeError:
        return []
    return tool_calls if isinstance(tool_calls, list) else []


@router.get("/history/{session_id}", response_model=ChatHistoryResponse)
def get_chat_history(session_id: str, db=Depends(get_db)):
    records = crud.list_chat_history_by_session(db, session_id)
    items = [
        ChatHistoryItem(
            id=record.id,
            session_id=record.session_id,
            device_code=record.device.device_code if record.device else None,
            question=record.question,
            answer=record.answer,
            sources=_decode_sources(record.sources_json),
            tool_calls=_decode_tool_calls(record.tool_calls_json),
            created_at=record.created_at,
        )
        for record in records
    ]
    return ChatHistoryResponse(
        message=f"查询到 {len(items)} 条聊天记录。",
        session_id=session_id,
        items=items,
    )
