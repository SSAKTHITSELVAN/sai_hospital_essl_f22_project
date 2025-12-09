from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Static password (in production, use proper authentication)
ADMIN_PASSWORD = "admin123"

class LoginRequest(BaseModel):
    password: str

@router.post("/login")
async def login(request: LoginRequest):
    if request.password == ADMIN_PASSWORD:
        return {
            "status": "success",
            "message": "Login successful",
            "data": {
                "token": "static_admin_token",
                "user": "admin"
            }
        }
    raise HTTPException(status_code=401, detail="Invalid password")

@router.post("/logout")
async def logout():
    return {
        "status": "success",
        "message": "Logged out successfully"
    }