from fastapi import APIRouter, Depends, HTTPException, Query

from app.db import crud
from app.db.session import get_db
from app.schemas.db import (
    AlarmRecordItem,
    AlarmRecordListResponse,
    DeviceDetailResponse,
    DeviceItem,
    DeviceListResponse,
    MaintenanceRecordItem,
    MaintenanceRecordListResponse,
)


router = APIRouter(prefix="/api/devices", tags=["devices"])


def _device_item(device) -> DeviceItem:
    return DeviceItem(
        device_code=device.device_code,
        device_name=device.device_name,
        device_type=device.device_type,
        location=device.location,
        manufacturer=device.manufacturer,
        install_date=device.install_date,
        status=device.status,
    )


def _get_device_or_404(db, device_code: str):
    device = crud.get_device_by_code(db, device_code)
    if device is None:
        raise HTTPException(status_code=404, detail=f"设备不存在：{device_code}")
    return device


@router.get("", response_model=DeviceListResponse)
def list_device_api(db=Depends(get_db)):
    devices = crud.list_devices(db)
    return DeviceListResponse(
        message="设备列表查询成功。",
        items=[_device_item(device) for device in devices],
    )


@router.get("/{device_code}", response_model=DeviceDetailResponse)
def get_device_api(device_code: str, db=Depends(get_db)):
    device = _get_device_or_404(db, device_code)
    return DeviceDetailResponse(message="设备详情查询成功。", item=_device_item(device))


@router.get("/{device_code}/alarms", response_model=AlarmRecordListResponse)
def list_alarm_records_api(
    device_code: str,
    limit: int = Query(5, ge=1, le=100, description="返回最近多少条报警记录"),
    db=Depends(get_db),
):
    device = _get_device_or_404(db, device_code)
    records = crud.list_alarm_records(db, device.id, limit=limit)
    return AlarmRecordListResponse(
        message="报警记录查询成功。",
        device_code=device.device_code,
        items=[
            AlarmRecordItem(
                alarm_code=record.alarm_code,
                alarm_level=record.alarm_level,
                alarm_message=record.alarm_message,
                occurred_at=record.occurred_at,
                resolved_at=record.resolved_at,
                status=record.status,
            )
            for record in records
        ],
    )


@router.get("/{device_code}/maintenance", response_model=MaintenanceRecordListResponse)
def list_maintenance_records_api(
    device_code: str,
    limit: int = Query(5, ge=1, le=100, description="返回最近多少条维修记录"),
    db=Depends(get_db),
):
    device = _get_device_or_404(db, device_code)
    records = crud.list_maintenance_records(db, device.id, limit=limit)
    return MaintenanceRecordListResponse(
        message="维修记录查询成功。",
        device_code=device.device_code,
        items=[
            MaintenanceRecordItem(
                work_order_no=record.work_order_no,
                fault_description=record.fault_description,
                root_cause=record.root_cause,
                solution=record.solution,
                maintainer=record.maintainer,
                started_at=record.started_at,
                finished_at=record.finished_at,
            )
            for record in records
        ],
    )
