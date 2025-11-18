

# app/schemas/response.py
from typing import Optional, Any, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar('T')


class StandardResponse(BaseModel, Generic[T]):
    """Standard API response format"""
    status: str
    message: str
    data: Optional[T] = None
    error: Optional[dict] = None

