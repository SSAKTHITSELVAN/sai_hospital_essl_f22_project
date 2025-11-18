# app/api/routes/attendance.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import date, datetime, timedelta
from typing import Optional

from app.core.database import get_db
from app.core.response import success_response, error_response
from app.models.attendance import AttendanceLog, ProcessedAttendance
from app.models.user import User
from app.services.attendance_processor import AttendanceProcessor

router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.get("/logs")
async def get_attendance_logs(
    uid: Optional[int] = Query(None, description="Filter by user UID"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Get raw attendance logs with filters"""
    try:
        query = db.query(AttendanceLog)
        
        if uid:
            query = query.filter(AttendanceLog.uid == uid)
        
        if start_date:
            query = query.filter(func.date(AttendanceLog.timestamp) >= start_date)
        
        if end_date:
            query = query.filter(func.date(AttendanceLog.timestamp) <= end_date)
        
        total = query.count()
        logs = query.order_by(AttendanceLog.timestamp.desc()).offset(skip).limit(limit).all()
        
        return success_response(
            message=f"Retrieved {len(logs)} attendance logs",
            data={
                "logs": [
                    {
                        "id": log.id,
                        "uid": log.uid,
                        "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                        "punch_type": log.punch_type,
                        "status": log.status,
                        "device_id": log.device_id
                    }
                    for log in logs
                ],
                "pagination": {
                    "skip": skip,
                    "limit": limit,
                    "total": total
                }
            }
        )
    except Exception as e:
        return error_response(
            message="Failed to retrieve attendance logs",
            error_details={"error": str(e)}
        )


@router.get("/processed")
async def get_processed_attendance(
    uid: Optional[int] = Query(None, description="Filter by user UID"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Get processed attendance records"""
    try:
        # Build query with explicit join
        query = db.query(ProcessedAttendance).join(
            User, 
            ProcessedAttendance.uid == User.uid
        )
        
        if uid:
            query = query.filter(ProcessedAttendance.uid == uid)
        
        if start_date:
            query = query.filter(ProcessedAttendance.date >= start_date)
        
        if end_date:
            query = query.filter(ProcessedAttendance.date <= end_date)
        
        # Get total count
        total = query.count()
        
        # Get records with pagination
        records = query.order_by(
            ProcessedAttendance.date.desc()
        ).offset(skip).limit(limit).all()
        
        return success_response(
            message=f"Retrieved {len(records)} processed attendance records",
            data={
                "records": [
                    {
                        "id": rec.id,
                        "uid": rec.uid,
                        "user_name": rec.user.name if rec.user else "Unknown",
                        "date": rec.date.isoformat(),
                        "shift": rec.shift.value if rec.shift else None,
                        "first_in": rec.first_in.isoformat() if rec.first_in else None,
                        "last_out": rec.last_out.isoformat() if rec.last_out else None,
                        "work_duration_hours": rec.work_duration_hours,
                        "status": rec.status.value if rec.status else None,
                        "is_late": rec.is_late,
                        "late_by_minutes": rec.late_by_minutes,
                        "is_early_leave": rec.is_early_leave,
                        "early_leave_by_minutes": rec.early_leave_by_minutes,
                        "total_punches": rec.total_punches,
                        "remarks": rec.remarks
                    }
                    for rec in records
                ],
                "pagination": {
                    "skip": skip,
                    "limit": limit,
                    "total": total
                }
            }
        )
    except Exception as e:
        import traceback
        traceback.print_exc()  # Print full error to console
        return error_response(
            message="Failed to retrieve processed attendance",
            error_details={"error": str(e)}
        )


@router.get("/summary/{uid}")
async def get_attendance_summary(
    uid: int,
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """Get attendance summary for a user"""
    try:
        # Check if user exists
        user = db.query(User).filter(User.uid == uid).first()
        if not user:
            return error_response(
                message=f"User with UID {uid} not found",
                error_details={"uid": uid}
            )
        
        processor = AttendanceProcessor(db)
        summary = processor.get_user_attendance_summary(uid, start_date, end_date)
        
        # Add user info
        summary["user"] = {
            "uid": user.uid,
            "name": user.name
        }
        
        return success_response(
            message="Attendance summary generated",
            data=summary
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return error_response(
            message="Failed to generate attendance summary",
            error_details={"error": str(e)}
        )


@router.post("/process")
async def process_attendance(
    uid: Optional[int] = Query(None, description="Process for specific user"),
    target_date: Optional[date] = Query(None, description="Process specific date"),
    db: Session = Depends(get_db)
):
    """Manually trigger attendance processing"""
    try:
        processor = AttendanceProcessor(db)
        
        if uid and target_date:
            # Process specific user and date
            result = processor.process_daily_attendance(uid, target_date)
            if result:
                return success_response(
                    message="Attendance processed successfully",
                    data={
                        "uid": result.uid,
                        "date": result.date.isoformat(),
                        "status": result.status.value,
                        "shift": result.shift.value,
                        "work_duration_hours": result.work_duration_hours
                    }
                )
            else:
                return error_response(
                    message="No attendance logs found for processing",
                    error_details={
                        "uid": uid,
                        "date": target_date.isoformat()
                    }
                )
        else:
            # Process all pending
            stats = processor.process_all_pending()
            return success_response(
                message="All pending attendance processed",
                data=stats
            )
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return error_response(
            message="Failed to process attendance",
            error_details={"error": str(e)}
        )


@router.get("/today")
async def get_today_attendance(
    db: Session = Depends(get_db)
):
    """Get today's attendance for all users"""
    try:
        today = date.today()
        
        records = db.query(ProcessedAttendance).join(
            User,
            ProcessedAttendance.uid == User.uid
        ).filter(
            ProcessedAttendance.date == today
        ).all()
        
        return success_response(
            message=f"Retrieved today's attendance for {len(records)} users",
            data={
                "date": today.isoformat(),
                "total_users": len(records),
                "records": [
                    {
                        "uid": rec.uid,
                        "name": rec.user.name if rec.user else "Unknown",
                        "shift": rec.shift.value if rec.shift else None,
                        "first_in": rec.first_in.isoformat() if rec.first_in else None,
                        "last_out": rec.last_out.isoformat() if rec.last_out else None,
                        "status": rec.status.value if rec.status else None,
                        "is_late": rec.is_late,
                        "work_duration_hours": rec.work_duration_hours
                    }
                    for rec in records
                ]
            }
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return error_response(
            message="Failed to retrieve today's attendance",
            error_details={"error": str(e)}
        )


@router.get("/stats")
async def get_attendance_stats(
    start_date: Optional[date] = Query(None, description="Start date"),
    end_date: Optional[date] = Query(None, description="End date"),
    db: Session = Depends(get_db)
):
    """Get overall attendance statistics"""
    try:
        from app.models.attendance import AttendanceStatus
        
        # Default to current month if no dates provided
        if not start_date:
            start_date = date.today().replace(day=1)
        if not end_date:
            end_date = date.today()
        
        # Get all records in date range
        records = db.query(ProcessedAttendance).filter(
            and_(
                ProcessedAttendance.date >= start_date,
                ProcessedAttendance.date <= end_date
            )
        ).all()
        
        # Calculate statistics
        total_records = len(records)
        present_count = sum(1 for r in records if r.status == AttendanceStatus.PRESENT)
        late_count = sum(1 for r in records if r.status == AttendanceStatus.LATE)
        early_leave_count = sum(1 for r in records if r.status == AttendanceStatus.EARLY_LEAVE)
        incomplete_count = sum(1 for r in records if r.status == AttendanceStatus.INCOMPLETE)
        half_day_count = sum(1 for r in records if r.status == AttendanceStatus.HALF_DAY)
        
        total_work_hours = sum(r.work_duration_hours for r in records if r.work_duration_hours)
        avg_work_hours = round(total_work_hours / total_records, 2) if total_records > 0 else 0
        
        return success_response(
            message="Attendance statistics retrieved",
            data={
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "statistics": {
                    "total_records": total_records,
                    "present": present_count,
                    "late": late_count,
                    "early_leave": early_leave_count,
                    "incomplete": incomplete_count,
                    "half_day": half_day_count,
                    "total_work_hours": round(total_work_hours, 2),
                    "average_work_hours": avg_work_hours
                },
                "percentages": {
                    "present": round(present_count / total_records * 100, 2) if total_records > 0 else 0,
                    "late": round(late_count / total_records * 100, 2) if total_records > 0 else 0,
                    "incomplete": round(incomplete_count / total_records * 100, 2) if total_records > 0 else 0
                }
            }
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return error_response(
            message="Failed to retrieve attendance statistics",
            error_details={"error": str(e)}
        )