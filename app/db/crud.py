import json
from typing import Optional
from uuid import uuid4

from app.db.models import AlarmRecord, ChatRecord, Device, DiagnosisReport, MaintenanceRecord


def list_devices(db) -> list:
    return db.query(Device).order_by(Device.device_code.asc()).all()


def get_device_by_code(db, device_code: str) -> Optional[Device]:
    return db.query(Device).filter(Device.device_code == device_code).first()


def list_alarm_records(db, device_id: int, limit: int = 5) -> list:
    return (
        db.query(AlarmRecord)
        .filter(AlarmRecord.device_id == device_id)
        .order_by(AlarmRecord.occurred_at.desc())
        .limit(limit)
        .all()
    )


def get_maintenance_by_work_order(db, work_order_no: str) -> Optional[MaintenanceRecord]:
    return db.query(MaintenanceRecord).filter(MaintenanceRecord.work_order_no == work_order_no).first()


def list_maintenance_records(db, device_id: int, limit: int = 5) -> list:
    return (
        db.query(MaintenanceRecord)
        .filter(MaintenanceRecord.device_id == device_id)
        .order_by(MaintenanceRecord.started_at.desc(), MaintenanceRecord.created_at.desc())
        .limit(limit)
        .all()
    )


def get_alarm_by_business_key(db, device_id: int, alarm_code: str, occurred_at) -> Optional[AlarmRecord]:
    return (
        db.query(AlarmRecord)
        .filter(
            AlarmRecord.device_id == device_id,
            AlarmRecord.alarm_code == alarm_code,
            AlarmRecord.occurred_at == occurred_at,
        )
        .first()
    )


def save_chat_record(
    db,
    session_id: str,
    question: str,
    answer: str,
    sources: list,
    tool_calls: Optional[list] = None,
    device_id: Optional[int] = None,
) -> ChatRecord:
    record = ChatRecord(
        session_id=session_id,
        device_id=device_id,
        question=question,
        answer=answer,
        sources_json=json.dumps(sources, ensure_ascii=False),
        tool_calls_json=json.dumps(tool_calls or [], ensure_ascii=False),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_chat_history_by_session(db, session_id: str) -> list:
    return (
        db.query(ChatRecord)
        .filter(ChatRecord.session_id == session_id)
        .order_by(ChatRecord.created_at.asc(), ChatRecord.id.asc())
        .all()
    )


def _decode_json(value: Optional[str], default):
    if not value:
        return default
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return default
    return decoded


def _diagnosis_report_to_dict(record: DiagnosisReport) -> dict:
    return {
        "report_id": record.report_id,
        "session_id": record.session_id,
        "device_code": record.device.device_code if record.device else None,
        "question": record.question,
        "report_markdown": record.report_markdown,
        "evidence": _decode_json(record.evidence_json, {}),
        "tool_calls": _decode_json(record.tool_calls_json, []),
        "created_at": record.created_at,
    }


def save_diagnosis_report(
    db,
    session_id: str,
    question: str,
    report_markdown: str,
    evidence: dict,
    tool_calls: list,
    device_id: Optional[int] = None,
    report_id: Optional[str] = None,
) -> dict:
    record = DiagnosisReport(
        report_id=report_id or str(uuid4()),
        session_id=session_id,
        device_id=device_id,
        question=question,
        report_markdown=report_markdown,
        evidence_json=json.dumps(evidence or {}, ensure_ascii=False),
        tool_calls_json=json.dumps(tool_calls or [], ensure_ascii=False),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _diagnosis_report_to_dict(record)


def get_diagnosis_report_by_report_id(db, report_id: str) -> Optional[dict]:
    record = db.query(DiagnosisReport).filter(DiagnosisReport.report_id == report_id).first()
    return _diagnosis_report_to_dict(record) if record else None


def get_diagnosis_reports_by_session_id(db, session_id: str) -> list:
    records = (
        db.query(DiagnosisReport)
        .filter(DiagnosisReport.session_id == session_id)
        .order_by(DiagnosisReport.created_at.asc(), DiagnosisReport.id.asc())
        .all()
    )
    return [_diagnosis_report_to_dict(record) for record in records]
