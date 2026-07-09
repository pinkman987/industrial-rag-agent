from datetime import date, datetime
from pathlib import Path
import sys
from typing import Dict

from sqlalchemy import inspect, text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.base import Base
from app.db.crud import get_alarm_by_business_key, get_device_by_code, get_maintenance_by_work_order
from app.db.models import AlarmRecord, Device, DiagnosisReport, MaintenanceRecord
from app.db.session import SessionLocal, engine


DEVICE_SEEDS = [
    {
        "device_code": "SV300-01",
        "device_name": "SV300伺服电机",
        "device_type": "伺服系统",
        "location": "一车间A线",
        "manufacturer": "华东自动化",
        "install_date": date(2023, 5, 18),
        "status": "running",
    },
    {
        "device_code": "CONV-A1",
        "device_name": "CONV_A1输送线",
        "device_type": "输送设备",
        "location": "装配车间",
        "manufacturer": "苏州输送装备",
        "install_date": date(2022, 9, 3),
        "status": "running",
    },
    {
        "device_code": "CNC-X200",
        "device_name": "CNC_X200数控加工中心",
        "device_type": "数控设备",
        "location": "机加工车间",
        "manufacturer": "星河数控",
        "install_date": date(2021, 11, 12),
        "status": "running",
    },
]

ALARM_SEEDS = [
    {
        "device_code": "SV300-01",
        "alarm_code": "E-05",
        "alarm_level": "major",
        "alarm_message": "伺服驱动器过载报警",
        "occurred_at": datetime(2026, 6, 20, 9, 15, 0),
        "resolved_at": datetime(2026, 6, 20, 10, 5, 0),
        "status": "resolved",
    },
    {
        "device_code": "SV300-01",
        "alarm_code": "E-07",
        "alarm_level": "warning",
        "alarm_message": "伺服电机过热报警",
        "occurred_at": datetime(2026, 6, 22, 14, 30, 0),
        "resolved_at": datetime(2026, 6, 22, 15, 10, 0),
        "status": "resolved",
    },
    {
        "device_code": "CONV-A1",
        "alarm_code": "A-21",
        "alarm_level": "major",
        "alarm_message": "输送电机过载",
        "occurred_at": datetime(2026, 6, 18, 11, 20, 0),
        "resolved_at": datetime(2026, 6, 18, 12, 0, 0),
        "status": "resolved",
    },
    {
        "device_code": "CNC-X200",
        "alarm_code": "S-14",
        "alarm_level": "major",
        "alarm_message": "主轴温度过高",
        "occurred_at": datetime(2026, 6, 25, 16, 45, 0),
        "resolved_at": datetime(2026, 6, 25, 18, 10, 0),
        "status": "resolved",
    },
]

MAINTENANCE_SEEDS = [
    {
        "device_code": "SV300-01",
        "work_order_no": "WO-SV300-001",
        "fault_description": "SV300伺服电机运行中出现E-05过载报警。",
        "root_cause": "导轨润滑不足，机械负载偏高，加减速时间设置偏短。",
        "solution": "清理导轨并补充润滑脂，延长加减速时间，复测负载电流。",
        "maintainer": "张工",
        "started_at": datetime(2026, 6, 20, 9, 30, 0),
        "finished_at": datetime(2026, 6, 20, 10, 20, 0),
    },
    {
        "device_code": "CONV-A1",
        "work_order_no": "WO-CONV-001",
        "fault_description": "CONV_A1输送线出现A-21输送电机过载报警。",
        "root_cause": "输送带张紧过度，入口处存在轻微物料堆积。",
        "solution": "调整皮带张力，清理入口堆积物，检查减速机温度。",
        "maintainer": "李工",
        "started_at": datetime(2026, 6, 18, 11, 30, 0),
        "finished_at": datetime(2026, 6, 18, 12, 15, 0),
    },
    {
        "device_code": "CNC-X200",
        "work_order_no": "WO-CNC-001",
        "fault_description": "CNC_X200加工中心长时间加工后出现S-14主轴温度过高。",
        "root_cause": "主轴冷却风扇积尘，润滑油液位偏低。",
        "solution": "清理风扇和散热片，补充润滑油，降低连续高速加工时长。",
        "maintainer": "王工",
        "started_at": datetime(2026, 6, 25, 17, 0, 0),
        "finished_at": datetime(2026, 6, 25, 18, 30, 0),
    },
]


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_chat_records_tool_calls_column()
    ensure_diagnosis_reports_table()
    print("数据库表创建完成。")


def ensure_chat_records_tool_calls_column() -> None:
    inspector = inspect(engine)
    if "chat_records" not in inspector.get_table_names():
        return
    column_names = {column["name"] for column in inspector.get_columns("chat_records")}
    if "tool_calls_json" in column_names:
        return
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE chat_records ADD COLUMN tool_calls_json TEXT"))
    print("chat_records.tool_calls_json 字段已补充。")


def ensure_diagnosis_reports_table() -> None:
    DiagnosisReport.__table__.create(bind=engine, checkfirst=True)


def seed_devices(db) -> Dict[str, Device]:
    devices = {}
    inserted = 0
    for seed in DEVICE_SEEDS:
        device = get_device_by_code(db, seed["device_code"])
        if device is None:
            device = Device(**seed)
            db.add(device)
            db.flush()
            inserted += 1
        devices[device.device_code] = device
    print(f"示例设备初始化完成，新增 {inserted} 条。")
    return devices


def seed_alarms(db, devices: Dict[str, Device]) -> None:
    inserted = 0
    for seed in ALARM_SEEDS:
        device = devices[seed["device_code"]]
        alarm = get_alarm_by_business_key(db, device.id, seed["alarm_code"], seed["occurred_at"])
        if alarm is not None:
            continue
        db.add(
            AlarmRecord(
                device_id=device.id,
                alarm_code=seed["alarm_code"],
                alarm_level=seed["alarm_level"],
                alarm_message=seed["alarm_message"],
                occurred_at=seed["occurred_at"],
                resolved_at=seed["resolved_at"],
                status=seed["status"],
            )
        )
        inserted += 1
    print(f"示例报警记录初始化完成，新增 {inserted} 条。")


def seed_maintenance(db, devices: Dict[str, Device]) -> None:
    inserted = 0
    for seed in MAINTENANCE_SEEDS:
        record = get_maintenance_by_work_order(db, seed["work_order_no"])
        if record is not None:
            continue
        device = devices[seed["device_code"]]
        db.add(
            MaintenanceRecord(
                device_id=device.id,
                work_order_no=seed["work_order_no"],
                fault_description=seed["fault_description"],
                root_cause=seed["root_cause"],
                solution=seed["solution"],
                maintainer=seed["maintainer"],
                started_at=seed["started_at"],
                finished_at=seed["finished_at"],
            )
        )
        inserted += 1
    print(f"示例维修记录初始化完成，新增 {inserted} 条。")


def main() -> None:
    create_tables()
    db = SessionLocal()
    try:
        devices = seed_devices(db)
        seed_alarms(db, devices)
        seed_maintenance(db, devices)
        db.commit()
        print("数据库初始化完成。")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
