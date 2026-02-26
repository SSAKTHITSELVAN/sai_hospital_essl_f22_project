# app/models/attendance.py
# IMPORTANT: Run this SQL migration after deploying this file:
#   ALTER TABLE processed_attendance ADD COLUMN IF NOT EXISTS overtime_hours FLOAT DEFAULT 0.0;
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Date, Enum, Float, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base


class PunchType(enum.Enum):
    CHECK_IN     = 0
    CHECK_OUT    = 1
    BREAK_OUT    = 2
    BREAK_IN     = 3
    OVERTIME_IN  = 4
    OVERTIME_OUT = 5


class ShiftType(enum.Enum):
    A = "A"  # Morning Shift     07:00-15:00
    B = "B"  # Afternoon Shift   15:00-23:00
    C = "C"  # Night Shift       23:00-07:00
    G = "G"  # General Shift     09:00-17:00


class AttendanceStatus(enum.Enum):
    PRESENT     = "present"
    LATE        = "late"
    EARLY_LEAVE = "early_leave"
    ABSENT      = "absent"
    INCOMPLETE  = "incomplete"
    HALF_DAY    = "half_day"
    LOP         = "lop"


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
    id    = Column(Integer, primary_key=True, index=True)
    uid   = Column(Integer, ForeignKey("users.uid"), nullable=False, index=True)
    date  = Column(Date, nullable=False, index=True)
    shift = Column(Enum(ShiftType), nullable=True)
    first_in               = Column(DateTime, nullable=True)
    last_out               = Column(DateTime, nullable=True)
    work_duration_hours    = Column(Float, nullable=True)
    overtime_hours         = Column(Float, nullable=True, default=0.0)
    status                 = Column(Enum(AttendanceStatus), nullable=False)
    is_late                = Column(Boolean, default=False)
    is_early_leave         = Column(Boolean, default=False)
    late_by_minutes        = Column(Integer, default=0)
    early_leave_by_minutes = Column(Integer, default=0)
    total_punches          = Column(Integer, default=0)
    remarks                = Column(String(500), nullable=True)
    created_at             = Column(DateTime, default=datetime.utcnow)
    updated_at             = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = relationship("User", back_populates="processed_attendance")