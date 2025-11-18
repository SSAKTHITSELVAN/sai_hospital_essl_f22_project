from typing import Optional, Any, Generic, TypeVar
from pydantic import BaseModel


T = TypeVar('T')


class StandardResponse(BaseModel, Generic[T]):
    """
    Standard API response format
    All endpoints return responses in this format
    """
    status: str  # "success" or "error"
    message: str
    data: Optional[T] = None
    error: Optional[dict] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Operation completed successfully",
                "data": {"example": "data"},
                "error": None
            }
        }


def success_response(
    message: str = "Operation successful",
    data: Any = None
) -> dict:
    """Create a success response"""
    return {
        "status": "success",
        "message": message,
        "data": data,
        "error": None
    }


def error_response(
    message: str = "Operation failed",
    error_details: Optional[dict] = None,
    data: Any = None
) -> dict:
    """Create an error response"""
    return {
        "status": "error",
        "message": message,
        "data": data,
        "error": error_details or {}
    }