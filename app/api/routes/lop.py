# app/api/routes/lop.py
from fastapi import APIRouter, Depends, Query, Body
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta
from typing import Optional, List

from app.core.database import get_db
from app.core.response import success_response, error_response
from app.services.lop_service import LOPService

router = APIRouter(prefix="/lop", tags=["LOP - Loss of Pay"])


@router.get("/absentees")
async def get_daily_absentees(
    target_date: Optional[date] = Query(None, description="Date to check (default: yesterday)"),
    db: Session = Depends(get_db)
):
    """
    Get list of absentees for a specific date
    Run this at 7 AM to check previous day's attendance
    """
    try:
        if not target_date:
            # Default to yesterday
            target_date = date.today() - timedelta(days=1)
        
        lop_service = LOPService(db)
        result = lop_service.get_absentees_for_date(target_date)
        
        return success_response(
            message=f"Absentee report for {target_date.isoformat()}",
            data=result
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return error_response(
            message="Failed to get absentees",
            error_details={"error": str(e)}
        )


@router.post("/mark")
async def mark_lop(
    target_date: date = Query(..., description="Date to mark LOP for"),
    exclude_uids: Optional[List[int]] = Body(None, description="UIDs to exclude (approved leave)"),
    db: Session = Depends(get_db)
):
    """
    Manually mark LOP for absentees on a specific date
    Optionally exclude users who are on approved leave
    """
    try:
        lop_service = LOPService(db)
        result = lop_service.mark_lop_for_date(target_date, exclude_uids)
        
        if result["status"] == "success":
            return success_response(
                message=f"LOP marked for {result['marked']} employees on {target_date.isoformat()}",
                data=result
            )
        else:
            return error_response(
                message=result.get("message", "Failed to mark LOP"),
                error_details=result
            )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return error_response(
            message="Failed to mark LOP",
            error_details={"error": str(e)}
        )


@router.get("/records")
async def get_lop_records(
    start_date: Optional[date] = Query(None, description="Start date"),
    end_date: Optional[date] = Query(None, description="End date"),
    uid: Optional[int] = Query(None, description="Filter by user UID"),
    db: Session = Depends(get_db)
):
    """
    Get all LOP records within a date range
    """
    try:
        lop_service = LOPService(db)
        records = lop_service.get_lop_records(start_date, end_date, uid)
        
        return success_response(
            message=f"Retrieved {len(records)} LOP records",
            data={
                "total": len(records),
                "records": records,
                "filters": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                    "uid": uid
                }
            }
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return error_response(
            message="Failed to retrieve LOP records",
            error_details={"error": str(e)}
        )


@router.get("/summary/{uid}")
async def get_user_lop_summary(
    uid: int,
    start_date: date = Query(..., description="Start date"),
    end_date: date = Query(..., description="End date"),
    db: Session = Depends(get_db)
):
    """
    Get LOP summary for a specific user
    Shows total LOP days and dates
    """
    try:
        lop_service = LOPService(db)
        summary = lop_service.get_lop_summary(uid, start_date, end_date)
        
        if "error" in summary:
            return error_response(
                message=summary["error"],
                error_details={"uid": uid}
            )
        
        return success_response(
            message=f"LOP summary for UID {uid}",
            data=summary
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return error_response(
            message="Failed to get LOP summary",
            error_details={"error": str(e)}
        )


@router.delete("/remove")
async def remove_lop_marking(
    uid: int = Query(..., description="User UID"),
    target_date: date = Query(..., description="Date to remove LOP from"),
    reason: Optional[str] = Body(None, description="Reason for removal"),
    db: Session = Depends(get_db)
):
    """
    Remove LOP marking for a user on a specific date
    Use this when employee submits approved leave
    """
    try:
        lop_service = LOPService(db)
        result = lop_service.remove_lop_marking(uid, target_date, reason)
        
        if result["status"] == "success":
            return success_response(
                message=result["message"],
                data=result
            )
        else:
            return error_response(
                message=result["message"],
                error_details=result
            )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return error_response(
            message="Failed to remove LOP marking",
            error_details={"error": str(e)}
        )


@router.get("/check-today")
async def check_today_absentees(db: Session = Depends(get_db)):
    """
    Quick endpoint to check today's absentees
    This runs at 7 AM to check yesterday's attendance
    """
    try:
        yesterday = date.today() - timedelta(days=1)
        
        lop_service = LOPService(db)
        result = lop_service.get_absentees_for_date(yesterday)
        
        return success_response(
            message=f"Yesterday's ({yesterday.isoformat()}) absentee check",
            data={
                "check_date": yesterday.isoformat(),
                "checked_at": datetime.now().isoformat(),
                "absentees": result
            }
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return error_response(
            message="Failed to check today's absentees",
            error_details={"error": str(e)}
        )


@router.post("/auto-mark-yesterday")
async def auto_mark_yesterday_lop(
    exclude_uids: Optional[List[int]] = Body(None, description="UIDs to exclude"),
    db: Session = Depends(get_db)
):
    """
    Automatically mark LOP for yesterday's absentees
    This should be called by the scheduled task at 7 AM
    """
    try:
        yesterday = date.today() - timedelta(days=1)
        
        lop_service = LOPService(db)
        result = lop_service.mark_lop_for_date(yesterday, exclude_uids)
        
        if result["status"] == "success":
            return success_response(
                message=f"Auto-marked LOP for yesterday ({yesterday.isoformat()})",
                data=result
            )
        else:
            return error_response(
                message="Failed to auto-mark LOP",
                error_details=result
            )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return error_response(
            message="Failed to auto-mark LOP",
            error_details={"error": str(e)}
        )