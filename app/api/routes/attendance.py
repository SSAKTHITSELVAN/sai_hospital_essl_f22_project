# app/api/routes/attendance.py
import json
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import date, datetime, timedelta
from typing import Optional

from app.core.database import get_db
from app.core.response import success_response, error_response
from app.models.attendance import AttendanceLog, ProcessedAttendance, AttendanceStatus
from app.models.user import User
from app.services.attendance_processor import AttendanceProcessor

router = APIRouter(prefix="/attendance", tags=["Attendance"])


def _serialize_record(rec: ProcessedAttendance) -> dict:
    """Serialize a ProcessedAttendance record including all punch sessions."""
    sessions = []
    if rec.punch_sessions:
        try:
            sessions = json.loads(rec.punch_sessions)
        except Exception:
            pass

    hours = rec.work_duration_hours or 0.0
    ot    = rec.overtime_hours      or 0.0

    return {
        "id":                   rec.id,
        "uid":                  rec.uid,
        "user_name":            rec.user.name if rec.user else "Unknown",
        "date":                 rec.date.isoformat(),
        "sessions":             sessions,           # [{in, out}, ...]
        "first_in":             rec.first_in.isoformat()  if rec.first_in  else None,
        "last_out":             rec.last_out.isoformat()  if rec.last_out  else None,
        "work_duration_hours":  round(hours, 2),
        "overtime_hours":       round(ot,    2),
        "status":               rec.status.value if rec.status else None,
        "total_punches":        rec.total_punches,
        "remarks":              rec.remarks,
        # kept for UI compatibility
        "shift":                None,
        "shift_label":          None,
        "is_late":              False,
        "late_by_minutes":      0,
        "is_early_leave":       False,
        "early_leave_by_minutes": 0,
    }


@router.get("/logs")
async def get_attendance_logs(
    uid: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date:   Optional[date] = Query(None),
    skip:  int = Query(0,   ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    try:
        query = db.query(AttendanceLog)
        if uid:        query = query.filter(AttendanceLog.uid == uid)
        if start_date: query = query.filter(func.date(AttendanceLog.timestamp) >= start_date)
        if end_date:   query = query.filter(func.date(AttendanceLog.timestamp) <= end_date)
        total = query.count()
        logs  = query.order_by(AttendanceLog.timestamp.desc()).offset(skip).limit(limit).all()
        return success_response(
            f"Retrieved {len(logs)} attendance logs",
            {
                "logs": [
                    {
                        "id":         log.id,
                        "uid":        log.uid,
                        "timestamp":  log.timestamp.isoformat() if log.timestamp else None,
                        "punch_type": log.punch_type,
                        "status":     log.status,
                        "device_id":  log.device_id,
                    }
                    for log in logs
                ],
                "pagination": {"skip": skip, "limit": limit, "total": total},
            },
        )
    except Exception as e:
        return error_response("Failed to retrieve attendance logs", {"error": str(e)})


@router.get("/processed")
async def get_processed_attendance(
    uid: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date:   Optional[date] = Query(None),
    skip:  int = Query(0,   ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    try:
        query = db.query(ProcessedAttendance).join(User, ProcessedAttendance.uid == User.uid)
        if uid:        query = query.filter(ProcessedAttendance.uid  == uid)
        if start_date: query = query.filter(ProcessedAttendance.date >= start_date)
        if end_date:   query = query.filter(ProcessedAttendance.date <= end_date)
        total   = query.count()
        records = query.order_by(ProcessedAttendance.date.desc()).offset(skip).limit(limit).all()
        return success_response(
            f"Retrieved {len(records)} processed attendance records",
            {
                "records":    [_serialize_record(r) for r in records],
                "pagination": {"skip": skip, "limit": limit, "total": total},
            },
        )
    except Exception as e:
        import traceback; traceback.print_exc()
        return error_response("Failed to retrieve processed attendance", {"error": str(e)})


@router.get("/summary/{uid}")
async def get_attendance_summary(
    uid: int,
    start_date: date = Query(...),
    end_date:   date = Query(...),
    detailed: bool = Query(False),
    export: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    try:
        user = db.query(User).filter(User.uid == uid).first()
        if not user:
            return error_response(f"User with UID {uid} not found", {"uid": uid})

        processor = AttendanceProcessor(db)
        if export and export.lower() == "csv":
            detailed = True

        summary = processor.get_user_attendance_summary(uid, start_date, end_date, detailed=detailed)
        summary["user"] = {"uid": user.uid, "name": user.name}

        if export and export.lower() == "csv":
            import io, csv
            from fastapi.responses import StreamingResponse

            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                "month", "date", "status",
                "first_in", "last_out",
                "work_duration_hours", "overtime_hours",
                "total_punches", "remarks",
            ])
            for m in summary.get("months", []):
                for d in m.get("days", []):
                    writer.writerow([
                        m.get("month"),
                        d.get("date"),
                        d.get("status"),
                        d.get("first_in"),
                        d.get("last_out"),
                        d.get("work_duration_hours"),
                        d.get("overtime_hours", 0),
                        d.get("total_punches"),
                        d.get("remarks"),
                    ])
            output.seek(0)
            filename = f"attendance_{uid}_{start_date}_{end_date}.csv"
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )

        return success_response("Attendance summary generated", summary)
    except Exception as e:
        import traceback; traceback.print_exc()
        return error_response("Failed to generate attendance summary", {"error": str(e)})


@router.post("/process")
async def process_attendance(
    uid: Optional[int] = Query(None),
    target_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    try:
        processor = AttendanceProcessor(db)
        if uid and target_date:
            result = processor.process_daily_attendance(uid, target_date)
            if result:
                return success_response("Attendance processed successfully", {
                    "uid":                  result.uid,
                    "date":                 result.date.isoformat(),
                    "status":               result.status.value,
                    "work_duration_hours":  result.work_duration_hours,
                    "overtime_hours":       result.overtime_hours or 0.0,
                })
            return error_response("No attendance logs found", {"uid": uid, "date": str(target_date)})
        stats = processor.process_all_pending()
        return success_response("All pending attendance processed", stats)
    except Exception as e:
        import traceback; traceback.print_exc()
        return error_response("Failed to process attendance", {"error": str(e)})


@router.get("/today")
async def get_today_attendance(db: Session = Depends(get_db)):
    try:
        today   = date.today()
        records = (
            db.query(ProcessedAttendance)
            .join(User, ProcessedAttendance.uid == User.uid)
            .filter(ProcessedAttendance.date == today)
            .all()
        )
        return success_response(
            f"Retrieved today's attendance for {len(records)} users",
            {
                "date":        today.isoformat(),
                "total_users": len(records),
                "records": [
                    {
                        "uid":                  rec.uid,
                        "name":                 rec.user.name if rec.user else "Unknown",
                        "first_in":             rec.first_in.isoformat()  if rec.first_in  else None,
                        "last_out":             rec.last_out.isoformat()  if rec.last_out  else None,
                        "status":               rec.status.value if rec.status else None,
                        "work_duration_hours":  rec.work_duration_hours,
                        "overtime_hours":       rec.overtime_hours or 0.0,
                        # UI compat
                        "shift":                None,
                        "shift_label":          None,
                        "is_late":              False,
                    }
                    for rec in records
                ],
            },
        )
    except Exception as e:
        import traceback; traceback.print_exc()
        return error_response("Failed to retrieve today's attendance", {"error": str(e)})


@router.get("/stats")
async def get_attendance_stats(
    start_date: Optional[date] = Query(None),
    end_date:   Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    try:
        if not start_date: start_date = date.today().replace(day=1)
        if not end_date:   end_date   = date.today()

        records = (
            db.query(ProcessedAttendance)
            .filter(
                and_(
                    ProcessedAttendance.date >= start_date,
                    ProcessedAttendance.date <= end_date,
                )
            )
            .all()
        )

        total       = len(records)
        present     = sum(1 for r in records if r.status in (AttendanceStatus.PRESENT, AttendanceStatus.PRESENT_OT))
        half_day    = sum(1 for r in records if r.status == AttendanceStatus.HALF_DAY)
        incomplete  = sum(1 for r in records if r.status == AttendanceStatus.INCOMPLETE)
        total_hours = sum(r.work_duration_hours or 0 for r in records)
        total_ot    = sum(r.overtime_hours      or 0 for r in records)
        avg_hours   = round(total_hours / total, 2) if total else 0

        return success_response("Attendance statistics retrieved", {
            "period":     {"start_date": str(start_date), "end_date": str(end_date)},
            "statistics": {
                "total_records":         total,
                "present":               present,
                "half_day":              half_day,
                "incomplete":            incomplete,
                "total_work_hours":      round(total_hours, 2),
                "total_overtime_hours":  round(total_ot,    2),
                "average_work_hours":    avg_hours,
            },
            "percentages": {
                "present":    round(present   / total * 100, 2) if total else 0,
                "half_day":   round(half_day  / total * 100, 2) if total else 0,
                "incomplete": round(incomplete/ total * 100, 2) if total else 0,
            },
        })
    except Exception as e:
        import traceback; traceback.print_exc()
        return error_response("Failed to retrieve attendance statistics", {"error": str(e)})