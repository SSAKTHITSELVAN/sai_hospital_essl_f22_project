# app/models/__init__.py
# ShiftType has been removed — the system no longer uses fixed shifts.
# Import only what exists in the updated attendance model.
from .attendance import (
    AttendanceLog,
    ProcessedAttendance,
    AttendanceStatus,
    PunchType,
)
from .user import User
from .device import Device