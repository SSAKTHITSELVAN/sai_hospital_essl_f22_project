
# app/schemas/user.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """Base user schema"""
    name: str = Field(..., min_length=1, max_length=100)
    uid: int = Field(..., gt=0)
    privilege: int = Field(default=0, ge=0, le=14)
    card_no: Optional[str] = None
    group_id: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a user"""
    password: Optional[str] = None


class UserUpdate(BaseModel):
    """Schema for updating a user"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    privilege: Optional[int] = Field(None, ge=0, le=14)
    card_no: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """Schema for user response"""
    id: int
    is_active: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Schema for user list response"""
    users: list[UserResponse]
    pagination: dict
