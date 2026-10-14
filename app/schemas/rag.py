from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Source(BaseModel):
    file_name: str
    page: Optional[int] = None
    chunk_index: Optional[int] = None
    similarity_score: float
    content_preview: str
    retrieval_mode: Optional[str] = None


class UploadResponse(BaseModel):
    message: str
    file_name: str
    chunk_count: int


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="设备故障或运维问题")
    session_id: Optional[str] = Field(default=None, description="可选会话ID，不传则由后端自动生成")
    device_code: Optional[str] = Field(default=None, description="可选设备编码，仅用于关联对话记录")


class AskResponse(BaseModel):
    message: str
    answer: str
    sources: list[Source]
    session_id: str


class ChatHistoryItem(BaseModel):
    id: int
    session_id: str
    device_code: Optional[str] = None
    question: str
    answer: str
    sources: list[Source]
    tool_calls: list = Field(default_factory=list)
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    message: str
    session_id: str
    items: list[ChatHistoryItem]
