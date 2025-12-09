# app/models/attendance.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Date, Time, Enum, Float, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base


class PunchType(enum.Enum):
    """Punch type enumeration"""
    CHECK_IN = 0
    CHECK_OUT = 1
    BREAK_OUT = 2
    BREAK_IN = 3
    OVERTIME_IN = 4
    OVERTIME_OUT = 5


class ShiftType(enum.Enum):
    """Shift type enumeration"""
    A = "A"  # Morning Shift (07:00-15:00)
    B = "B"  # Afternoon Shift (15:00-23:00)
    C = "C"  # Night Shift (23:00-07:00)
    G = "G"  # General Shift (09:00-17:00)


class AttendanceStatus(enum.Enum):
    """Attendance status enumeration"""
    PRESENT = "present"
    LATE = "late"
    EARLY_LEAVE = "early_leave"
    ABSENT = "absent"
    INCOMPLETE = "incomplete"  # Only IN or only OUT
    HALF_DAY = "half_day"
    LOP = "lop"  # Loss of Pay - absent across all shifts


class AttendanceLog(Base):
    """Raw attendance logs from device"""
    __tablename__ = "attendance_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    uid = Column(Integer, ForeignKey("users.uid"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    punch_type = Column(Integer, default=0)  # 0=IN, 1=OUT
    status = Column(Integer, default=0)
    device_id = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="attendance_logs")


class ProcessedAttendance(Base):
    """Processed attendance records with shift detection"""
    __tablename__ = "processed_attendance"
    
    id = Column(Integer, primary_key=True, index=True)
    uid = Column(Integer, ForeignKey("users.uid"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    shift = Column(Enum(ShiftType), nullable=True)  # NULL for LOP records
    
    # Time tracking
    first_in = Column(DateTime, nullable=True)
    last_out = Column(DateTime, nullable=True)
    
    # Calculated fields
    work_duration_hours = Column(Float, nullable=True)  # Hours worked
    status = Column(Enum(AttendanceStatus), nullable=False)
    is_late = Column(Boolean, default=False)
    is_early_leave = Column(Boolean, default=False)
    late_by_minutes = Column(Integer, default=0)
    early_leave_by_minutes = Column(Integer, default=0)
    
    # Additional info
    total_punches = Column(Integer, default=0)  # Number of punches that day
    remarks = Column(String(500), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="processed_attendance")