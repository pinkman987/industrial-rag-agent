from datetime import datetime
from typing import Optional

try:
    from pydantic import BaseModel, Field
except ModuleNotFoundError:
    class BaseModel:
        def __init__(self, **data):
            for key, value in data.items():
                setattr(self, key, value)

    def Field(default, **_kwargs):
        return default


class DiagnosisRequest(BaseModel):
    question: str = Field(..., min_length=1, description="设备故障或运维诊断问题")
    session_id: Optional[str] = Field(default=None, description="可选会话ID，不传则由后端自动生成")
    device_code: Optional[str] = Field(default=None, description="可选设备编码，用于关联业务数据")


class DiagnosisResponse(BaseModel):
    message: str
    diagnosis: str
    evidence: dict
    tool_calls: list
    session_id: str


class DiagnosisReportRequest(BaseModel):
    question: str = Field(..., min_length=1, description="设备故障诊断报告问题")
    session_id: Optional[str] = Field(default=None, description="可选会话ID，不传则由后端自动生成")
    device_code: Optional[str] = Field(default=None, description="可选设备编码，用于关联业务数据")


class DiagnosisReportResponse(BaseModel):
    message: str
    report_id: str
    report_markdown: str
    evidence: dict
    tool_calls: list
    session_id: str


class DiagnosisReportHistoryItem(BaseModel):
    report_id: str
    session_id: str
    device_code: Optional[str] = None
    question: str
    report_markdown: str
    evidence: dict
    tool_calls: list
    created_at: datetime


class DiagnosisReportHistoryResponse(BaseModel):
    message: str
    session_id: str
    items: list[DiagnosisReportHistoryItem]
