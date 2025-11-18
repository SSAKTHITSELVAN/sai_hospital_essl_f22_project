# app/api/routes/payroll.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, extract
from datetime import date, datetime, timedelta
from typing import Optional, Dict, List
from collections import defaultdict
import calendar

from app.core.database import get_db
from app.core.response import success_response, error_response
from app.models.attendance import ProcessedAttendance, AttendanceStatus, ShiftType
from app.models.user import User

router = APIRouter(prefix="/payroll", tags=["Payroll & Reports"])


def get_week_number(date_obj: date) -> int:
    """Get week number of month (1-5)"""
    first_day = date_obj.replace(day=1)
    adjusted_dom = date_obj.day + first_day.weekday()
    return int((adjusted_dom - 1) / 7) + 1


@router.get("/detailed-report/{uid}")
async def get_detailed_payroll_report(
    uid: int,
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive payroll report with:
    - Monthly breakdown
    - Weekly breakdown
    - Shift-wise analysis
    - Leave tracking
    - Work hours summary
    """
    try:
        # Check if user exists
        user = db.query(User).filter(User.uid == uid).first()
        if not user:
            return error_response(
                message=f"User with UID {uid} not found",
                error_details={"uid": uid}
            )
        
        # Get all attendance records
        records = db.query(ProcessedAttendance).filter(
            and_(
                ProcessedAttendance.uid == uid,
                ProcessedAttendance.date >= start_date,
                ProcessedAttendance.date <= end_date
            )
        ).order_by(ProcessedAttendance.date).all()
        
        if not records:
            return success_response(
                message="No attendance records found for the period",
                data={
                    "user": {"uid": user.uid, "name": user.name},
                    "period": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat()
                    },
                    "summary": {},
                    "monthly_breakdown": [],
                    "weekly_breakdown": [],
                    "shift_analysis": {},
                    "leave_summary": {}
                }
            )
        
        # Initialize data structures
        monthly_data = defaultdict(lambda: {
            'total_days': 0,
            'present_days': 0,
            'late_days': 0,
            'early_leave_days': 0,
            'incomplete_days': 0,
            'half_days': 0,
            'leaves': 0,
            'total_hours': 0.0,
            'overtime_hours': 0.0,
            'shift_breakdown': defaultdict(lambda: {
                'days': 0, 'hours': 0.0, 'late_count': 0, 'leaves': 0
            })
        })
        
        weekly_data = defaultdict(lambda: {
            'start_date': None,
            'end_date': None,
            'total_days': 0,
            'present_days': 0,
            'total_hours': 0.0,
            'leaves': 0
        })
        
        shift_summary = defaultdict(lambda: {
            'total_days': 0,
            'present_days': 0,
            'late_days': 0,
            'leaves': 0,
            'total_hours': 0.0,
            'avg_hours': 0.0
        })
        
        # Calculate expected working days
        total_calendar_days = (end_date - start_date).days + 1
        expected_working_days = total_calendar_days  # Adjust based on your policy
        
        # Process each record
        for record in records:
            month_key = record.date.strftime('%Y-%m')
            week_key = f"{record.date.year}-W{get_week_number(record.date)}-{record.date.strftime('%B')}"
            shift_key = record.shift.value if record.shift else "Unknown"
            
            # Monthly aggregation
            monthly_data[month_key]['total_days'] += 1
            
            if record.status == AttendanceStatus.PRESENT:
                monthly_data[month_key]['present_days'] += 1
            elif record.status == AttendanceStatus.LATE:
                monthly_data[month_key]['late_days'] += 1
            elif record.status == AttendanceStatus.EARLY_LEAVE:
                monthly_data[month_key]['early_leave_days'] += 1
            elif record.status == AttendanceStatus.INCOMPLETE:
                monthly_data[month_key]['incomplete_days'] += 1
            elif record.status == AttendanceStatus.HALF_DAY:
                monthly_data[month_key]['half_days'] += 1
            
            if record.work_duration_hours:
                monthly_data[month_key]['total_hours'] += record.work_duration_hours
                
                # Calculate overtime (if worked more than 8 hours)
                if record.work_duration_hours > 8:
                    monthly_data[month_key]['overtime_hours'] += (record.work_duration_hours - 8)
            
            # Shift breakdown within month
            monthly_data[month_key]['shift_breakdown'][shift_key]['days'] += 1
            if record.work_duration_hours:
                monthly_data[month_key]['shift_breakdown'][shift_key]['hours'] += record.work_duration_hours
            if record.is_late:
                monthly_data[month_key]['shift_breakdown'][shift_key]['late_count'] += 1
            
            # Weekly aggregation
            if weekly_data[week_key]['start_date'] is None:
                # Calculate week start and end
                week_start = record.date - timedelta(days=record.date.weekday())
                week_end = week_start + timedelta(days=6)
                weekly_data[week_key]['start_date'] = week_start.isoformat()
                weekly_data[week_key]['end_date'] = week_end.isoformat()
            
            weekly_data[week_key]['total_days'] += 1
            if record.status in [AttendanceStatus.PRESENT, AttendanceStatus.LATE]:
                weekly_data[week_key]['present_days'] += 1
            if record.work_duration_hours:
                weekly_data[week_key]['total_hours'] += record.work_duration_hours
            
            # Shift summary
            shift_summary[shift_key]['total_days'] += 1
            if record.status in [AttendanceStatus.PRESENT, AttendanceStatus.LATE]:
                shift_summary[shift_key]['present_days'] += 1
            if record.is_late:
                shift_summary[shift_key]['late_days'] += 1
            if record.work_duration_hours:
                shift_summary[shift_key]['total_hours'] += record.work_duration_hours
        
        # Calculate leaves for each month
        for month_key, data in monthly_data.items():
            year, month = map(int, month_key.split('-'))
            days_in_month = calendar.monthrange(year, month)[1]
            
            # Calculate leaves (days in month - days worked)
            month_start = date(year, month, 1)
            month_end = date(year, month, days_in_month)
            
            # Adjust for query date range
            actual_start = max(month_start, start_date)
            actual_end = min(month_end, end_date)
            expected_days_in_month = (actual_end - actual_start).days + 1
            
            data['leaves'] = expected_days_in_month - data['total_days']
        
        # Calculate averages for shifts
        for shift_key, data in shift_summary.items():
            if data['total_days'] > 0:
                data['avg_hours'] = round(data['total_hours'] / data['total_days'], 2)
            data['leaves'] = expected_working_days - data['total_days']
        
        # Overall summary
        total_worked_days = len(records)
        total_present = sum(1 for r in records if r.status == AttendanceStatus.PRESENT)
        total_late = sum(1 for r in records if r.status == AttendanceStatus.LATE)
        total_early_leave = sum(1 for r in records if r.status == AttendanceStatus.EARLY_LEAVE)
        total_incomplete = sum(1 for r in records if r.status == AttendanceStatus.INCOMPLETE)
        total_half_days = sum(1 for r in records if r.status == AttendanceStatus.HALF_DAY)
        total_leaves = expected_working_days - total_worked_days
        
        total_hours = sum(r.work_duration_hours for r in records if r.work_duration_hours)
        total_overtime = sum(
            r.work_duration_hours - 8 
            for r in records 
            if r.work_duration_hours and r.work_duration_hours > 8
        )
        
        avg_hours_per_day = round(total_hours / total_worked_days, 2) if total_worked_days > 0 else 0
        
        # Format monthly breakdown
        monthly_breakdown = []
        for month_key in sorted(monthly_data.keys()):
            data = monthly_data[month_key]
            year, month = map(int, month_key.split('-'))
            month_name = calendar.month_name[month]
            
            monthly_breakdown.append({
                "month": f"{month_name} {year}",
                "month_key": month_key,
                "total_days_worked": data['total_days'],
                "present_days": data['present_days'],
                "late_days": data['late_days'],
                "early_leave_days": data['early_leave_days'],
                "incomplete_days": data['incomplete_days'],
                "half_days": data['half_days'],
                "leaves": data['leaves'],
                "total_hours": round(data['total_hours'], 2),
                "overtime_hours": round(data['overtime_hours'], 2),
                "average_hours_per_day": round(
                    data['total_hours'] / data['total_days'], 2
                ) if data['total_days'] > 0 else 0,
                "shift_breakdown": {
                    shift: {
                        "days_worked": shift_data['days'],
                        "hours_worked": round(shift_data['hours'], 2),
                        "late_count": shift_data['late_count'],
                        "average_hours": round(
                            shift_data['hours'] / shift_data['days'], 2
                        ) if shift_data['days'] > 0 else 0
                    }
                    for shift, shift_data in data['shift_breakdown'].items()
                }
            })
        
        # Format weekly breakdown
        weekly_breakdown = []
        for week_key in sorted(weekly_data.keys()):
            data = weekly_data[week_key]
            weekly_breakdown.append({
                "week": week_key,
                "start_date": data['start_date'],
                "end_date": data['end_date'],
                "days_worked": data['total_days'],
                "present_days": data['present_days'],
                "total_hours": round(data['total_hours'], 2),
                "average_hours_per_day": round(
                    data['total_hours'] / data['total_days'], 2
                ) if data['total_days'] > 0 else 0
            })
        
        # Format shift analysis
        shift_analysis = {
            shift: {
                "total_days_worked": data['total_days'],
                "present_days": data['present_days'],
                "late_days": data['late_days'],
                "leaves": data['leaves'],
                "total_hours": round(data['total_hours'], 2),
                "average_hours_per_day": data['avg_hours'],
                "attendance_rate": round(
                    (data['present_days'] / data['total_days'] * 100), 2
                ) if data['total_days'] > 0 else 0
            }
            for shift, data in shift_summary.items()
        }
        
        # Leave summary
        leave_summary = {
            "total_calendar_days": total_calendar_days,
            "total_worked_days": total_worked_days,
            "total_leaves": total_leaves,
            "leave_percentage": round((total_leaves / total_calendar_days * 100), 2),
            "incomplete_days": total_incomplete,
            "half_days": total_half_days
        }
        
        return success_response(
            message="Detailed payroll report generated",
            data={
                "user": {
                    "uid": user.uid,
                    "name": user.name,
                    "card_no": user.card_no
                },
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "total_days": total_calendar_days
                },
                "summary": {
                    "total_worked_days": total_worked_days,
                    "present_days": total_present,
                    "late_days": total_late,
                    "early_leave_days": total_early_leave,
                    "incomplete_days": total_incomplete,
                    "half_days": total_half_days,
                    "leaves": total_leaves,
                    "total_hours_worked": round(total_hours, 2),
                    "overtime_hours": round(total_overtime, 2),
                    "average_hours_per_day": avg_hours_per_day,
                    "attendance_rate": round((total_worked_days / total_calendar_days * 100), 2)
                },
                "monthly_breakdown": monthly_breakdown,
                "weekly_breakdown": weekly_breakdown,
                "shift_analysis": shift_analysis,
                "leave_summary": leave_summary
            }
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return error_response(
            message="Failed to generate payroll report",
            error_details={"error": str(e)}
        )


@router.get("/monthly-summary/{uid}")
async def get_monthly_summary(
    uid: int,
    year: int = Query(..., description="Year (e.g., 2024)"),
    month: int = Query(..., ge=1, le=12, description="Month (1-12)"),
    db: Session = Depends(get_db)
):
    """Get detailed monthly summary for payroll"""
    try:
        # Get month start and end dates
        days_in_month = calendar.monthrange(year, month)[1]
        start_date = date(year, month, 1)
        end_date = date(year, month, days_in_month)
        
        # Check if user exists
        user = db.query(User).filter(User.uid == uid).first()
        if not user:
            return error_response(
                message=f"User with UID {uid} not found",
                error_details={"uid": uid}
            )
        
        # Get all records for the month
        records = db.query(ProcessedAttendance).filter(
            and_(
                ProcessedAttendance.uid == uid,
                ProcessedAttendance.date >= start_date,
                ProcessedAttendance.date <= end_date
            )
        ).order_by(ProcessedAttendance.date).all()
        
        # Daily breakdown
        daily_records = []
        for record in records:
            daily_records.append({
                "date": record.date.isoformat(),
                "day_of_week": record.date.strftime('%A'),
                "shift": record.shift.value if record.shift else None,
                "first_in": record.first_in.strftime('%H:%M:%S') if record.first_in else None,
                "last_out": record.last_out.strftime('%H:%M:%S') if record.last_out else None,
                "work_hours": record.work_duration_hours,
                "status": record.status.value if record.status else None,
                "is_late": record.is_late,
                "late_by_minutes": record.late_by_minutes,
                "is_early_leave": record.is_early_leave,
                "early_leave_by_minutes": record.early_leave_by_minutes,
                "remarks": record.remarks
            })
        
        # Calculate summary
        total_hours = sum(r.work_duration_hours for r in records if r.work_duration_hours)
        overtime_hours = sum(
            r.work_duration_hours - 8 
            for r in records 
            if r.work_duration_hours and r.work_duration_hours > 8
        )
        
        return success_response(
            message=f"Monthly summary for {calendar.month_name[month]} {year}",
            data={
                "user": {"uid": user.uid, "name": user.name},
                "month": calendar.month_name[month],
                "year": year,
                "summary": {
                    "total_days_in_month": days_in_month,
                    "days_worked": len(records),
                    "leaves": days_in_month - len(records),
                    "total_hours": round(total_hours, 2),
                    "overtime_hours": round(overtime_hours, 2),
                    "average_hours_per_day": round(total_hours / len(records), 2) if records else 0
                },
                "daily_records": daily_records
            }
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return error_response(
            message="Failed to generate monthly summary",
            error_details={"error": str(e)}
        )


@router.get("/shift-report")
async def get_shift_report(
    start_date: date = Query(..., description="Start date"),
    end_date: date = Query(..., description="End date"),
    shift: Optional[str] = Query(None, description="Filter by shift (A/B/C/G)"),
    db: Session = Depends(get_db)
):
    """Get shift-wise attendance report for all users"""
    try:
        query = db.query(ProcessedAttendance).join(User).filter(
            and_(
                ProcessedAttendance.date >= start_date,
                ProcessedAttendance.date <= end_date
            )
        )
        
        if shift:
            query = query.filter(ProcessedAttendance.shift == ShiftType[shift])
        
        records = query.all()
        
        # Group by shift and user
        shift_data = defaultdict(lambda: defaultdict(lambda: {
            'days': 0, 'hours': 0.0, 'late_count': 0, 'name': ''
        }))
        
        for record in records:
            shift_key = record.shift.value if record.shift else "Unknown"
            uid = record.uid
            
            shift_data[shift_key][uid]['name'] = record.user.name if record.user else "Unknown"
            shift_data[shift_key][uid]['days'] += 1
            if record.work_duration_hours:
                shift_data[shift_key][uid]['hours'] += record.work_duration_hours
            if record.is_late:
                shift_data[shift_key][uid]['late_count'] += 1
        
        # Format report
        report = {}
        for shift_key, users in shift_data.items():
            report[shift_key] = {
                "total_employees": len(users),
                "employees": [
                    {
                        "uid": uid,
                        "name": data['name'],
                        "days_worked": data['days'],
                        "total_hours": round(data['hours'], 2),
                        "late_days": data['late_count'],
                        "average_hours": round(data['hours'] / data['days'], 2) if data['days'] > 0 else 0
                    }
                    for uid, data in users.items()
                ]
            }
        
        return success_response(
            message="Shift report generated",
            data={
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "shifts": report
            }
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return error_response(
            message="Failed to generate shift report",
            error_details={"error": str(e)}
        )