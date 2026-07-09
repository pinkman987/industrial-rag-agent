from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class DeviceItem(BaseModel):
    device_code: str
    device_name: str
    device_type: Optional[str] = None
    location: Optional[str] = None
    manufacturer: Optional[str] = None
    install_date: Optional[date] = None
    status: Optional[str] = None


class DeviceListResponse(BaseModel):
    message: str
    items: list[DeviceItem]


class DeviceDetailResponse(BaseModel):
    message: str
    item: DeviceItem


class AlarmRecordItem(BaseModel):
    alarm_code: str
    alarm_level: Optional[str] = None
    alarm_message: Optional[str] = None
    occurred_at: datetime
    resolved_at: Optional[datetime] = None
    status: Optional[str] = None


class AlarmRecordListResponse(BaseModel):
    message: str
    device_code: str
    items: list[AlarmRecordItem]


class MaintenanceRecordItem(BaseModel):
    work_order_no: str
    fault_description: Optional[str] = None
    root_cause: Optional[str] = None
    solution: Optional[str] = None
    maintainer: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class MaintenanceRecordListResponse(BaseModel):
    message: str
    device_code: str
    items: list[MaintenanceRecordItem]
