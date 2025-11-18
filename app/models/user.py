# app/models/user.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class User(Base):
    """User model - stores employee information"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    uid = Column(Integer, unique=True, index=True, nullable=False)  # Device UID
    name = Column(String(100), nullable=False)
    privilege = Column(Integer, default=0)  # User privilege level
    password = Column(String(50), nullable=True)
    group_id = Column(String(50), nullable=True)
    user_id_str = Column(String(50), nullable=True)
    card_no = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    attendance_logs = relationship("AttendanceLog", back_populates="user")
    processed_attendance = relationship("ProcessedAttendance", back_populates="user")

