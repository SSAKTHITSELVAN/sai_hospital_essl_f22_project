

# app/api/routes/device.py
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.response import success_response, error_response
from app.services.device_sync import DeviceSyncService

router = APIRouter(prefix="/device", tags=["Device"])


@router.post("/sync")
async def trigger_sync(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Manually trigger device synchronization"""
    try:
        sync_service = DeviceSyncService(db)
        result = sync_service.full_sync()
        
        if result["status"] == "success":
            return success_response(
                message="Device synchronization completed",
                data=result
            )
        else:
            return error_response(
                message="Device synchronization failed",
                error_details={"error": result.get("error", "Unknown error")}
            )
    except Exception as e:
        return error_response(
            message="Failed to sync device",
            error_details={"error": str(e)}
        )


@router.get("/info")
async def get_device_info(db: Session = Depends(get_db)):
    """Get device information"""
    try:
        sync_service = DeviceSyncService(db)
        if sync_service.connect():
            info = sync_service.get_device_info()
            sync_service.disconnect()
            
            return success_response(
                message="Device information retrieved",
                data=info
            )
        else:
            return error_response(
                message="Failed to connect to device"
            )
    except Exception as e:
        return error_response(
            message="Failed to get device info",
            error_details={"error": str(e)}
        )

