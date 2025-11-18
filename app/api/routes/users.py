# app/api/routes/users.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.response import success_response, error_response
from app.models.user import User

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("")
async def get_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Get all users with pagination"""
    try:
        users = db.query(User).offset(skip).limit(limit).all()
        total = db.query(User).count()
        
        return success_response(
            message=f"Retrieved {len(users)} users",
            data={
                "users": [
                    {
                        "id": u.id,
                        "uid": u.uid,
                        "name": u.name,
                        "privilege": u.privilege,
                        "card_no": u.card_no,
                        "is_active": u.is_active,
                        "created_at": u.created_at.isoformat() if u.created_at else None
                    }
                    for u in users
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
            message="Failed to retrieve users",
            error_details={"error": str(e)}
        )


@router.get("/{uid}")
async def get_user_by_uid(
    uid: int,
    db: Session = Depends(get_db)
):
    """Get user by UID"""
    try:
        user = db.query(User).filter(User.uid == uid).first()
        
        if not user:
            return error_response(
                message=f"User with UID {uid} not found",
                error_details={"uid": uid}
            )
        
        return success_response(
            message="User found",
            data={
                "id": user.id,
                "uid": user.uid,
                "name": user.name,
                "privilege": user.privilege,
                "card_no": user.card_no,
                "group_id": user.group_id,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None
            }
        )
    except Exception as e:
        return error_response(
            message="Failed to retrieve user",
            error_details={"error": str(e)}
        )


# app/api/routes/attendance.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import date, datetime, timedelta
from app.core.database import get_db
from app.core.response import success_response, error_response
from app.models.attendance import AttendanceLog, ProcessedAttendance
from app.models.user import User
from app.services.attendance_processor import AttendanceProcessor

router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.get("/logs")
async def get_attendance_logs(
    uid: int = Query(None, description="Filter by user UID"),
    start_date: date = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(None, description="End date (YYYY-MM-DD)"),
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
                        "status": log.status
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
    uid: int = Query(None, description="Filter by user UID"),
    start_date: date = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """Get processed attendance records"""
    try:
        query = db.query(ProcessedAttendance).join(User)
        
        if uid:
            query = query.filter(ProcessedAttendance.uid == uid)
        
        if start_date:
            query = query.filter(ProcessedAttendance.date >= start_date)
        
        if end_date:
            query = query.filter(ProcessedAttendance.date <= end_date)
        
        records = query.order_by(ProcessedAttendance.date.desc()).all()
        
        return success_response(
            message=f"Retrieved {len(records)} processed attendance records",
            data={
                "records": [
                    {
                        "id": rec.id,
                        "uid": rec.uid,
                        "user_name": rec.user.name,
                        "date": rec.date.isoformat(),
                        "shift": rec.shift.value,
                        "first_in": rec.first_in.isoformat() if rec.first_in else None,
                        "last_out": rec.last_out.isoformat() if rec.last_out else None,
                        "work_duration_hours": rec.work_duration_hours,
                        "status": rec.status.value,
                        "is_late": rec.is_late,
                        "late_by_minutes": rec.late_by_minutes,
                        "is_early_leave": rec.is_early_leave,
                        "early_leave_by_minutes": rec.early_leave_by_minutes,
                        "total_punches": rec.total_punches,
                        "remarks": rec.remarks
                    }
                    for rec in records
                ]
            }
        )
    except Exception as e:
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
        processor = AttendanceProcessor(db)
        summary = processor.get_user_attendance_summary(uid, start_date, end_date)
        
        return success_response(
            message="Attendance summary generated",
            data=summary
        )
    except Exception as e:
        return error_response(
            message="Failed to generate attendance summary",
            error_details={"error": str(e)}
        )


@router.post("/process")
async def process_attendance(
    uid: int = Query(None, description="Process for specific user"),
    target_date: date = Query(None, description="Process specific date"),
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
                        "status": result.status.value
                    }
                )
            else:
                return error_response(
                    message="No attendance logs found for processing"
                )
        else:
            # Process all pending
            stats = processor.process_all_pending()
            return success_response(
                message="All pending attendance processed",
                data=stats
            )
            
    except Exception as e:
        return error_response(
            message="Failed to process attendance",
            error_details={"error": str(e)}
        )


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


# app/api/routes/iclock.py
from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.database import get_db
from app.models.attendance import AttendanceLog
from app.services.attendance_processor import AttendanceProcessor

router = APIRouter(prefix="/iclock", tags=["iClock Protocol"])


@router.post("/cdata")
@router.get("/cdata")
async def iclock_cdata(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Endpoint for F22 device to push attendance data
    Device sends data to: http://YOUR_IP:8000/iclock/cdata
    """
    try:
        # Parse device data
        if request.method == "POST":
            body = await request.body()
            data_str = body.decode('utf-8')
        else:
            data_str = str(request.query_params)
        
        print(f"📥 Received data from device: {data_str}")
        
        # Parse attendance records
        # Format: ATTLOG PIN=X&Time=YYYY-MM-DD HH:MM:SS&Status=0&Verify=1
        if "ATTLOG" in data_str:
            records = parse_attlog(data_str)
            
            for record in records:
                # Save to database
                log = AttendanceLog(
                    uid=record["pin"],
                    timestamp=record["timestamp"],
                    punch_type=record.get("status", 0),
                    status=record.get("verify", 0),
                    device_id=record.get("sn")
                )
                db.add(log)
            
            db.commit()
            
            # Process attendance immediately
            processor = AttendanceProcessor(db)
            for record in records:
                processor.process_daily_attendance(
                    record["pin"],
                    record["timestamp"].date()
                )
            
            return "OK"
        
        return "OK"
        
    except Exception as e:
        print(f"❌ Error processing device data: {e}")
        return "OK"  # Always return OK to device


def parse_attlog(data: str) -> list:
    """Parse ATTLOG format from device"""
    records = []
    lines = data.split('\n')
    
    for line in lines:
        if "PIN=" in line:
            record = {}
            parts = line.split('&')
            
            for part in parts:
                if '=' in part:
                    key, value = part.split('=', 1)
                    key = key.strip().lower()
                    
                    if key == "pin":
                        record["pin"] = int(value)
                    elif key == "time":
                        record["timestamp"] = datetime.strptime(
                            value, "%Y-%m-%d %H:%M:%S"
                        )
                    elif key == "status":
                        record["status"] = int(value)
                    elif key == "verify":
                        record["verify"] = int(value)
                    elif key == "sn":
                        record["sn"] = value
            
            if "pin" in record and "timestamp" in record:
                records.append(record)
    
    return records