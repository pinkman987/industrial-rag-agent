from fastapi import APIRouter, Depends, HTTPException

from app.db import crud
from app.db.session import get_db
from app.schemas.tools import ToolAskRequest, ToolAskResponse
from app.tools.tool_chat import ask_with_tools


router = APIRouter(prefix="/api/chat", tags=["tool-chat"])


@router.post("/ask-with-tools", response_model=ToolAskResponse)
def ask_question_with_tools(payload: ToolAskRequest, db=Depends(get_db)):
    try:
        result = ask_with_tools(
            question=payload.question,
            session_id=payload.session_id,
            device_code=payload.device_code,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    device = crud.get_device_by_code(db, payload.device_code) if payload.device_code else None
    crud.save_chat_record(
        db,
        session_id=result["session_id"],
        question=payload.question,
        answer=result["answer"],
        sources=result["sources"],
        tool_calls=result["tool_calls"],
        device_id=device.id if device else None,
    )
    return ToolAskResponse(**result)
