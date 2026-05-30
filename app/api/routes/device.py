# app/api/routes/device.py
"""
Key fix: /device/info now uses get_info_safe() which:
  - Does NOT call disable_device() on the fingerprint scanner
  - Uses the threading lock with a short timeout (non-blocking if busy)
  - Is safe to poll frequently from the frontend (every 30 seconds)
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import success_response, error_response
from app.services.device_sync import DeviceSyncService

router = APIRouter(prefix="/device", tags=["Device"])


@router.post("/sync")
async def trigger_sync(db: Session = Depends(get_db)):
    """Manually trigger a full device synchronization."""
    try:
        sync_service = DeviceSyncService(db)
        result       = sync_service.full_sync()

        if result["status"] == "success":
            return success_response("Device synchronization completed", result)
        else:
            return error_response(
                "Device synchronization failed",
                {"error": result.get("error", "Unknown error")},
            )
    except Exception as e:
        return error_response("Failed to sync device", {"error": str(e)})


@router.get("/info")
async def get_device_info(db: Session = Depends(get_db)):
    """
    Get device information.

    Uses get_info_safe() — does NOT disable the fingerprint scanner,
    so employees can still punch in/out while this is polled.
    Returns empty data (not an error) if the device is busy or offline.
    """
    try:
        sync_service = DeviceSyncService(db)
        info         = sync_service.get_info_safe()

        if info:
            return success_response("Device information retrieved", info)
        else:
            return error_response("Device offline or busy")
    except Exception as e:
        return error_response("Failed to get device info", {"error": str(e)})