
# app/schemas/attendance.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date


class AttendanceLogBase(BaseModel):
    """Base attendance log schema"""
    uid: int
    timestamp: datetime
    punch_type: int = Field(default=0, ge=0)
    status: int = Field(default=0)


class AttendanceLogCreate(AttendanceLogBase):
    """Schema for creating attendance log"""
    device_id: Optional[str] = None


class AttendanceLogResponse(AttendanceLogBase):
    """Schema for attendance log response"""
    id: int
    device_id: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class ProcessedAttendanceBase(BaseModel):
    """Base processed attendance schema"""
    uid: int
    date: date
    shift: str


class ProcessedAttendanceResponse(ProcessedAttendanceBase):
    """Schema for processed attendance response"""
    id: int
    user_name: str
    first_in: Optional[datetime]
    last_out: Optional[datetime]
    work_duration_hours: Optional[float]
    status: str
    is_late: bool
    late_by_minutes: int
    is_early_leave: bool
    early_leave_by_minutes: int
    total_punches: int
    remarks: Optional[str]
    
    class Config:
        from_attributes = True


class AttendanceSummaryResponse(BaseModel):
    """Schema for attendance summary response"""
    uid: int
    period: dict
    summary: dict


class AttendanceReportRequest(BaseModel):
    """Schema for attendance report request"""
    uid: Optional[int] = None
    start_date: date
    end_date: date


# app/schemas/device.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DeviceInfo(BaseModel):
    """Device information schema"""
    ip: str
    port: int
    firmware_version: Optional[str]
    serial_number: Optional[str]
    platform: Optional[str]
    device_name: Optional[str]
    mac_address: Optional[str]


class SyncResult(BaseModel):
    """Sync result schema"""
    status: str
    timestamp: str
    users: dict
    logs: dict
    processed_attendance: dict
    device_info: dict


class DeviceResponse(BaseModel):
    """Device response schema"""
    id: int
    device_ip: str
    device_port: int
    device_name: Optional[str]
    serial_number: Optional[str]
    firmware_version: Optional[str]
    is_active: bool
    last_sync_at: Optional[datetime]
    last_sync_status: Optional[str]
    last_sync_message: Optional[str]
    
    class Config:
        from_attributes = True