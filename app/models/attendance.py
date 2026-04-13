# app/models/attendance.py
#
# SQL migration (run once):
#   ALTER TABLE processed_attendance
#       ADD COLUMN IF NOT EXISTS punch_sessions TEXT    DEFAULT NULL,
#       ADD COLUMN IF NOT EXISTS overtime_hours FLOAT   DEFAULT 0.0;
#   ALTER TYPE attendancestatus ADD VALUE IF NOT EXISTS 'present_ot';
#   ALTER TABLE processed_attendance ALTER COLUMN shift DROP NOT NULL;
#
from sqlalchemy import (
    Column, Integer, String, DateTime,
    ForeignKey, Date, Enum, Float, Boolean, Text,
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base


class AttendanceStatus(enum.Enum):
    PRESENT    = "present"      # >= PRESENT_HOURS, no OT
    PRESENT_OT = "present_ot"  # >= PRESENT_HOURS + overtime
    HALF_DAY   = "half_day"     # >= HALF_DAY_HOURS and < PRESENT_HOURS
    INCOMPLETE = "incomplete"   # > 0 hrs but < HALF_DAY_HOURS
    ABSENT     = "absent"       # no punches at all
    LOP        = "lop"          # manually marked Loss-of-Pay


class PunchType(enum.Enum):
    CHECK_IN     = 0
    CHECK_OUT    = 1
    BREAK_OUT    = 2
    BREAK_IN     = 3
    OVERTIME_IN  = 4
    OVERTIME_OUT = 5


class AttendanceLog(Base):
    __tablename__ = "attendance_logs"

    id         = Column(Integer, primary_key=True, index=True)
    uid        = Column(Integer, ForeignKey("users.uid"), nullable=False, index=True)
    timestamp  = Column(DateTime, nullable=False, index=True)
    punch_type = Column(Integer, default=0)
    status     = Column(Integer, default=0)
    device_id  = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="attendance_logs")


class ProcessedAttendance(Base):
    __tablename__ = "processed_attendance"

    id   = Column(Integer, primary_key=True, index=True)
    uid  = Column(Integer, ForeignKey("users.uid"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)

    # JSON: [{"in": ISO, "out": ISO}, ...]  — always 1 or 2 sessions
    punch_sessions = Column(Text, nullable=True)

    # shift label stored as plain string: "Regular" or "Break Shift"
    shift = Column(String(20), nullable=True)

    first_in            = Column(DateTime, nullable=True)
    last_out            = Column(DateTime, nullable=True)
    work_duration_hours = Column(Float,   nullable=True)
    overtime_hours      = Column(Float,   nullable=True, default=0.0)
    total_punches       = Column(Integer, default=0)

    status   = Column(Enum(AttendanceStatus), nullable=False)
    remarks  = Column(String(500), nullable=True)

    # kept for DB compatibility — always False/0 in new records
    is_late                = Column(Boolean, default=False)
    is_early_leave         = Column(Boolean, default=False)
    late_by_minutes        = Column(Integer, default=0)
    early_leave_by_minutes = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="processed_attendance")