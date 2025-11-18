
# app/models/device.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from datetime import datetime
from app.core.database import Base


class Device(Base):
    """Device information and sync status"""
    __tablename__ = "devices"
    
    id = Column(Integer, primary_key=True, index=True)
    device_ip = Column(String(50), unique=True, nullable=False)
    device_port = Column(Integer, default=4370)
    device_name = Column(String(100), nullable=True)
    serial_number = Column(String(100), nullable=True)
    firmware_version = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Sync tracking
    last_sync_at = Column(DateTime, nullable=True)
    last_sync_status = Column(String(20), nullable=True)  # success/failed
    last_sync_message = Column(String(500), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)