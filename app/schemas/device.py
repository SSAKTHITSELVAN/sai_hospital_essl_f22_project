
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