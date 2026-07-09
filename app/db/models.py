from datetime import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_code = Column(String(64), unique=True, nullable=False, index=True)
    device_name = Column(String(128), nullable=False)
    device_type = Column(String(128))
    location = Column(String(128))
    manufacturer = Column(String(128))
    install_date = Column(Date, nullable=True)
    status = Column(String(32), default="running")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    alarms = relationship("AlarmRecord", back_populates="device")
    maintenance_records = relationship("MaintenanceRecord", back_populates="device")
    chat_records = relationship("ChatRecord", back_populates="device")
    diagnosis_reports = relationship("DiagnosisReport", back_populates="device")


class AlarmRecord(Base):
    __tablename__ = "alarm_records"
    __table_args__ = (
        UniqueConstraint("device_id", "alarm_code", "occurred_at", name="uq_alarm_device_code_time"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(ForeignKey("devices.id"), nullable=False, index=True)
    alarm_code = Column(String(64), nullable=False)
    alarm_level = Column(String(32))
    alarm_message = Column(String(255))
    occurred_at = Column(DateTime, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    status = Column(String(32), default="resolved")
    created_at = Column(DateTime, default=datetime.utcnow)

    device = relationship("Device", back_populates="alarms")


class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(ForeignKey("devices.id"), nullable=False, index=True)
    work_order_no = Column(String(64), unique=True, nullable=False, index=True)
    fault_description = Column(Text)
    root_cause = Column(Text)
    solution = Column(Text)
    maintainer = Column(String(64))
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    device = relationship("Device", back_populates="maintenance_records")


class ChatRecord(Base):
    __tablename__ = "chat_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), nullable=False, index=True)
    device_id = Column(ForeignKey("devices.id"), nullable=True, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    sources_json = Column(Text)
    tool_calls_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    device = relationship("Device", back_populates="chat_records")


class DiagnosisReport(Base):
    __tablename__ = "diagnosis_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(String(64), unique=True, nullable=False, index=True)
    session_id = Column(String(64), nullable=False, index=True)
    device_id = Column(ForeignKey("devices.id"), nullable=True, index=True)
    question = Column(Text, nullable=False)
    report_markdown = Column(Text, nullable=False)
    evidence_json = Column(Text)
    tool_calls_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    device = relationship("Device", back_populates="diagnosis_reports")
