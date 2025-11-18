from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
from app.models.attendance import (
    AttendanceLog, 
    ProcessedAttendance, 
    ShiftType, 
    AttendanceStatus
)
from app.models.user import User
from app.services.shift_detector import ShiftDetector


class AttendanceProcessor:
    """
    Processes raw attendance logs into meaningful attendance records
    Handles edge cases like missing OUT punches, multiple punches, etc.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.shift_detector = ShiftDetector()
    
    def process_daily_attendance(
        self, 
        uid: int, 
        target_date: date
    ) -> Optional[ProcessedAttendance]:
        """
        Process all attendance logs for a user on a specific date
        
        Args:
            uid: User ID
            target_date: Date to process
            
        Returns:
            ProcessedAttendance record or None if no logs
        """
        # Get all logs for this user on this date
        logs = self.db.query(AttendanceLog).filter(
            and_(
                AttendanceLog.uid == uid,
                func.date(AttendanceLog.timestamp) == target_date
            )
        ).order_by(AttendanceLog.timestamp).all()
        
        if not logs:
            return None
        
        # Detect shift from first punch
        first_log = logs[0]
        shift = self.shift_detector.detect_shift(first_log.timestamp)
        
        # Find first IN and last OUT
        first_in = None
        last_out = None
        
        for log in logs:
            if log.punch_type == 0 and first_in is None:  # First IN
                first_in = log.timestamp
            if log.punch_type == 1:  # Any OUT
                last_out = log.timestamp
        
        # Calculate work duration
        work_duration = None
        if first_in and last_out:
            work_duration = self.shift_detector.calculate_work_duration(
                first_in, last_out
            )
        
        # Determine attendance status and lateness
        status = self._determine_status(first_in, last_out, shift, work_duration)
        is_late, late_by = False, 0
        is_early_leave, early_by = False, 0
        remarks = []
        
        if first_in:
            is_late, late_by = self.shift_detector.calculate_late_minutes(
                first_in, shift
            )
        else:
            remarks.append("Missing check-in punch")
        
        if last_out:
            is_early_leave, early_by = self.shift_detector.calculate_early_leave_minutes(
                last_out, shift
            )
        else:
            remarks.append("Missing check-out punch")
        
        # Check if record already exists
        existing = self.db.query(ProcessedAttendance).filter(
            and_(
                ProcessedAttendance.uid == uid,
                ProcessedAttendance.date == target_date,
                ProcessedAttendance.shift == shift
            )
        ).first()
        
        if existing:
            # Update existing record
            existing.first_in = first_in
            existing.last_out = last_out
            existing.work_duration_hours = work_duration
            existing.status = status
            existing.is_late = is_late
            existing.is_early_leave = is_early_leave
            existing.late_by_minutes = late_by
            existing.early_leave_by_minutes = early_by
            existing.total_punches = len(logs)
            existing.remarks = "; ".join(remarks) if remarks else None
            existing.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(existing)
            return existing
        
        # Create new record
        processed = ProcessedAttendance(
            uid=uid,
            date=target_date,
            shift=shift,
            first_in=first_in,
            last_out=last_out,
            work_duration_hours=work_duration,
            status=status,
            is_late=is_late,
            is_early_leave=is_early_leave,
            late_by_minutes=late_by,
            early_leave_by_minutes=early_by,
            total_punches=len(logs),
            remarks="; ".join(remarks) if remarks else None
        )
        
        self.db.add(processed)
        self.db.commit()
        self.db.refresh(processed)
        
        return processed
    
    def _determine_status(
        self, 
        first_in: Optional[datetime],
        last_out: Optional[datetime],
        shift: ShiftType,
        work_duration: Optional[float]
    ) -> AttendanceStatus:
        """
        Determine overall attendance status
        
        Logic:
        - INCOMPLETE: Only IN or only OUT
        - ABSENT: No punches (shouldn't happen here)
        - HALF_DAY: Less than 4 hours worked
        - LATE: Checked in late
        - EARLY_LEAVE: Left early
        - PRESENT: Normal attendance
        """
        # No punches
        if not first_in and not last_out:
            return AttendanceStatus.ABSENT
        
        # Only IN or only OUT
        if not first_in or not last_out:
            return AttendanceStatus.INCOMPLETE
        
        # Check work duration
        if work_duration:
            expected_hours = self.shift_detector.get_expected_shift_hours(shift)
            
            # Less than half shift hours
            if work_duration < (expected_hours / 2):
                return AttendanceStatus.HALF_DAY
        
        # Check if late
        is_late, _ = self.shift_detector.calculate_late_minutes(first_in, shift)
        if is_late:
            return AttendanceStatus.LATE
        
        # Check if early leave
        is_early, _ = self.shift_detector.calculate_early_leave_minutes(last_out, shift)
        if is_early:
            return AttendanceStatus.EARLY_LEAVE
        
        # Normal attendance
        return AttendanceStatus.PRESENT
    
    def process_date_range(
        self, 
        uid: int, 
        start_date: date, 
        end_date: date
    ) -> List[ProcessedAttendance]:
        """
        Process attendance for a user across a date range
        
        Args:
            uid: User ID
            start_date: Start date
            end_date: End date
            
        Returns:
            List of ProcessedAttendance records
        """
        results = []
        current_date = start_date
        
        while current_date <= end_date:
            processed = self.process_daily_attendance(uid, current_date)
            if processed:
                results.append(processed)
            current_date += timedelta(days=1)
        
        return results
    
    def process_all_pending(self) -> Dict[str, int]:
        """
        Process all unprocessed attendance logs
        
        Returns:
            Dictionary with processing statistics
        """
        # Get distinct dates and users from attendance logs
        query = self.db.query(
            AttendanceLog.uid,
            func.date(AttendanceLog.timestamp).label('log_date')
        ).distinct()
        
        pending = query.all()
        
        processed_count = 0
        error_count = 0
        
        for uid, log_date in pending:
            try:
                self.process_daily_attendance(uid, log_date)
                processed_count += 1
            except Exception as e:
                print(f"Error processing attendance for UID {uid} on {log_date}: {e}")
                error_count += 1
        
        return {
            "processed": processed_count,
            "errors": error_count,
            "total": len(pending)
        }
    
    def get_user_attendance_summary(
        self, 
        uid: int, 
        start_date: date, 
        end_date: date
    ) -> Dict:
        """
        Get attendance summary for a user
        
        Returns:
            Dictionary with attendance statistics
        """
        records = self.db.query(ProcessedAttendance).filter(
            and_(
                ProcessedAttendance.uid == uid,
                ProcessedAttendance.date >= start_date,
                ProcessedAttendance.date <= end_date
            )
        ).all()
        
        total_days = len(records)
        present_days = sum(1 for r in records if r.status == AttendanceStatus.PRESENT)
        late_days = sum(1 for r in records if r.status == AttendanceStatus.LATE)
        early_leave_days = sum(1 for r in records if r.status == AttendanceStatus.EARLY_LEAVE)
        half_days = sum(1 for r in records if r.status == AttendanceStatus.HALF_DAY)
        incomplete_days = sum(1 for r in records if r.status == AttendanceStatus.INCOMPLETE)
        
        total_hours = sum(r.work_duration_hours for r in records if r.work_duration_hours)
        avg_hours = round(total_hours / total_days, 2) if total_days > 0 else 0
        
        return {
            "uid": uid,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "summary": {
                "total_days": total_days,
                "present": present_days,
                "late": late_days,
                "early_leave": early_leave_days,
                "half_day": half_days,
                "incomplete": incomplete_days,
                "total_hours_worked": round(total_hours, 2),
                "average_hours_per_day": avg_hours
            }
        }