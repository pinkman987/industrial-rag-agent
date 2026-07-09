from typing import Any, Optional

try:
    from pydantic import BaseModel, Field
except ModuleNotFoundError:
    class BaseModel:
        def __init__(self, **data):
            for key, value in data.items():
                setattr(self, key, value)

    def Field(default, **_kwargs):
        return default


class ToolAskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="设备故障或运维问题")
    session_id: Optional[str] = Field(default=None, description="可选会话ID，不传则由后端自动生成")
    device_code: Optional[str] = Field(default=None, description="可选设备编码，用于工具查询")


class ToolCallRecord(BaseModel):
    tool_name: str
    arguments: dict[str, Any]
    success: bool
    summary: str
    result_preview: str


class ToolAskResponse(BaseModel):
    message: str
    answer: str
    sources: list
    tool_calls: list[ToolCallRecord]
    session_id: str
