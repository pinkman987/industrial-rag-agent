from typing import Optional

from app.db import crud


def SessionLocal():
    from app.db.session import SessionLocal as _SessionLocal

    return _SessionLocal()


def _to_iso(value) -> Optional[str]:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _device_to_dict(device) -> dict:
    return {
        "device_code": device.device_code,
        "device_name": device.device_name,
        "device_type": device.device_type,
        "location": device.location,
        "manufacturer": device.manufacturer,
        "install_date": _to_iso(device.install_date),
        "status": device.status,
    }


def _alarm_to_dict(record) -> dict:
    return {
        "alarm_code": record.alarm_code,
        "alarm_level": record.alarm_level,
        "alarm_message": record.alarm_message,
        "occurred_at": _to_iso(record.occurred_at),
        "resolved_at": _to_iso(record.resolved_at),
        "status": record.status,
    }


def _maintenance_to_dict(record) -> dict:
    return {
        "work_order_no": record.work_order_no,
        "fault_description": record.fault_description,
        "root_cause": record.root_cause,
        "solution": record.solution,
        "maintainer": record.maintainer,
        "started_at": _to_iso(record.started_at),
        "finished_at": _to_iso(record.finished_at),
    }


def _device_not_found(tool_name: str, device_code: str, data) -> dict:
    return {
        "success": False,
        "tool_name": tool_name,
        "device_code": device_code,
        "data": data,
        "summary": f"设备不存在：{device_code}",
    }


def _database_error(tool_name: str, device_code: str, data, exc: Exception) -> dict:
    return {
        "success": False,
        "tool_name": tool_name,
        "device_code": device_code,
        "data": data,
        "summary": f"数据库查询失败：{exc}",
    }


def query_device_info(device_code: str) -> dict:
    tool_name = "query_device_info"
    db = None
    try:
        db = SessionLocal()
        device = crud.get_device_by_code(db, device_code)
        if device is None:
            return _device_not_found(tool_name, device_code, None)
        return {
            "success": True,
            "tool_name": tool_name,
            "device_code": device_code,
            "data": _device_to_dict(device),
            "summary": "已查询到设备基础信息。",
        }
    except Exception as exc:
        return _database_error(tool_name, device_code, None, exc)
    finally:
        if db is not None:
            db.close()


def query_alarm_records(device_code: str, limit: int = 5) -> dict:
    tool_name = "query_alarm_records"
    db = None
    try:
        db = SessionLocal()
        device = crud.get_device_by_code(db, device_code)
        if device is None:
            return _device_not_found(tool_name, device_code, [])
        records = crud.list_alarm_records(db, device.id, limit=limit)
        return {
            "success": True,
            "tool_name": tool_name,
            "device_code": device_code,
            "data": [_alarm_to_dict(record) for record in records],
            "summary": "已查询到设备近期报警记录。",
        }
    except Exception as exc:
        return _database_error(tool_name, device_code, [], exc)
    finally:
        if db is not None:
            db.close()


def query_maintenance_records(device_code: str, limit: int = 5) -> dict:
    tool_name = "query_maintenance_records"
    db = None
    try:
        db = SessionLocal()
        device = crud.get_device_by_code(db, device_code)
        if device is None:
            return _device_not_found(tool_name, device_code, [])
        records = crud.list_maintenance_records(db, device.id, limit=limit)
        return {
            "success": True,
            "tool_name": tool_name,
            "device_code": device_code,
            "data": [_maintenance_to_dict(record) for record in records],
            "summary": "已查询到设备历史维修记录。",
        }
    except Exception as exc:
        return _database_error(tool_name, device_code, [], exc)
    finally:
        if db is not None:
            db.close()
