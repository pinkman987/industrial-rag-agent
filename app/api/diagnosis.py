try:
    from fastapi import APIRouter, Depends, HTTPException
except ModuleNotFoundError:
    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str):
            self.status_code = status_code
            self.detail = detail
            super().__init__(detail)

    def Depends(_dependency=None):
        return None

    class APIRouter:
        def __init__(self, *args, **kwargs):
            pass

        def post(self, *args, **kwargs):
            def decorator(func):
                return func

            return decorator

        def get(self, *args, **kwargs):
            def decorator(func):
                return func

            return decorator

from uuid import uuid4

from app.db import crud
from app.diagnosis.report_generator import generate_markdown_report
from app.diagnosis.fault_diagnosis import analyze_fault
from app.schemas.diagnosis import (
    DiagnosisReportHistoryItem,
    DiagnosisReportHistoryResponse,
    DiagnosisReportRequest,
    DiagnosisReportResponse,
    DiagnosisRequest,
    DiagnosisResponse,
)


router = APIRouter(prefix="/api/diagnosis", tags=["diagnosis"])


def _get_db_dependency():
    from app.db.session import get_db

    yield from get_db()


def _is_usable_db_session(db) -> bool:
    return hasattr(db, "query") and hasattr(db, "add") and hasattr(db, "commit")


@router.post("/analyze", response_model=DiagnosisResponse)
def analyze_fault_api(payload: DiagnosisRequest):
    try:
        result = analyze_fault(
            question=payload.question,
            session_id=payload.session_id,
            device_code=payload.device_code,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return DiagnosisResponse(**result)


@router.post("/report", response_model=DiagnosisReportResponse)
def generate_diagnosis_report_api(payload: DiagnosisReportRequest, db=Depends(_get_db_dependency)):
    try:
        diagnosis_result = analyze_fault(
            question=payload.question,
            session_id=payload.session_id,
            device_code=payload.device_code,
        )
        report_markdown = generate_markdown_report(
            question=payload.question,
            device_code=payload.device_code,
            diagnosis_result=diagnosis_result,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    report_id = str(uuid4())
    if _is_usable_db_session(db):
        try:
            device = crud.get_device_by_code(db, payload.device_code) if payload.device_code else None
            saved_report = crud.save_diagnosis_report(
                db,
                report_id=report_id,
                session_id=diagnosis_result["session_id"],
                device_id=device.id if device else None,
                question=payload.question,
                report_markdown=report_markdown,
                evidence=diagnosis_result["evidence"],
                tool_calls=diagnosis_result["tool_calls"],
            )
            report_id = saved_report["report_id"]
        except Exception as exc:
            if hasattr(db, "rollback"):
                db.rollback()
            raise HTTPException(status_code=500, detail=f"诊断报告已生成，但保存失败：{exc}") from exc

    return DiagnosisReportResponse(
        message="已生成Markdown诊断报告。",
        report_id=report_id,
        report_markdown=report_markdown,
        evidence=diagnosis_result["evidence"],
        tool_calls=diagnosis_result["tool_calls"],
        session_id=diagnosis_result["session_id"],
    )


@router.get("/reports/{report_id}", response_model=DiagnosisReportHistoryItem)
def get_diagnosis_report_api(report_id: str, db=Depends(_get_db_dependency)):
    if not _is_usable_db_session(db):
        raise HTTPException(status_code=500, detail="数据库会话不可用，无法查询诊断报告。")
    report = crud.get_diagnosis_report_by_report_id(db, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"未查询到诊断报告：{report_id}")
    return DiagnosisReportHistoryItem(**report)


@router.get("/reports/session/{session_id}", response_model=DiagnosisReportHistoryResponse)
def get_diagnosis_reports_by_session_api(session_id: str, db=Depends(_get_db_dependency)):
    if not _is_usable_db_session(db):
        raise HTTPException(status_code=500, detail="数据库会话不可用，无法查询诊断报告历史。")
    reports = crud.get_diagnosis_reports_by_session_id(db, session_id)
    return DiagnosisReportHistoryResponse(
        message=f"查询到 {len(reports)} 份诊断报告。",
        session_id=session_id,
        items=[DiagnosisReportHistoryItem(**report) for report in reports],
    )
