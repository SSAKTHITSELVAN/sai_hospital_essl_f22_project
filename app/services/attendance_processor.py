# app/services/attendance_processor.py
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
    Processes raw attendance logs into meaningful attendance records.
    Handles: shift detection, overtime, missing OUT punches, multiple punches.
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
        Process all attendance logs for a user on a specific date.

        Key behaviours:
          - Shift is ALWAYS assigned from the first punch time. Never None.
          - If the F22 device sends all punches as punch_type=0 (all-IN),
            the last timestamp with a gap >= 1 hour is treated as checkout.
          - Overtime = minutes worked past shift end, converted to hours.
        """
        logs = self.db.query(AttendanceLog).filter(
            and_(
                AttendanceLog.uid == uid,
                func.date(AttendanceLog.timestamp) == target_date
            )
        ).order_by(AttendanceLog.timestamp).all()

        if not logs:
            return None

        # ── Always assign a shift from the first punch ────────────────── #
        shift = self.shift_detector.detect_shift(logs[0].timestamp)
        if shift is None:
            shift = ShiftType.G  # ultimate fallback - should not happen

        # ── Classify punches ──────────────────────────────────────────── #
        in_punches  = [l.timestamp for l in logs if l.punch_type == 0]
        out_punches = [l.timestamp for l in logs if l.punch_type == 1]

        first_in = min(in_punches)  if in_punches  else None
        last_out = max(out_punches) if out_punches  else None

        # F22 fallback: device sends everything as punch_type=0
        # If we have 2+ IN punches and zero OUT punches, and gap >= 1 hour,
        # treat last IN as checkout.
        inferred_out = False
        if in_punches and not out_punches and len(in_punches) >= 2:
            sorted_ins = sorted(in_punches)
            gap_hours = (sorted_ins[-1] - sorted_ins[0]).total_seconds() / 3600
            if gap_hours >= 1.0:
                first_in    = sorted_ins[0]
                last_out    = sorted_ins[-1]
                inferred_out = True

        # ── Work duration ─────────────────────────────────────────────── #
        work_duration = None
        if first_in and last_out:
            work_duration = self.shift_detector.calculate_work_duration(first_in, last_out)

        # ── Overtime ──────────────────────────────────────────────────── #
        overtime_hours = 0.0
        if last_out and shift:
            overtime_hours = self._calculate_overtime(last_out, shift, target_date)

        # ── Status / lateness / early-leave ───────────────────────────── #
        status   = self._determine_status(first_in, last_out, shift, work_duration)
        is_late  = False
        late_by  = 0
        is_early = False
        early_by = 0
        remarks  = []

        if first_in:
            is_late, late_by = self.shift_detector.calculate_late_minutes(first_in, shift)
        else:
            remarks.append("Missing check-in punch")

        if last_out:
            is_early, early_by = self.shift_detector.calculate_early_leave_minutes(last_out, shift)
        else:
            remarks.append("Missing check-out punch")

        if inferred_out:
            remarks.append("Checkout inferred from last punch")

        if overtime_hours > 0:
            remarks.append(f"Overtime: {overtime_hours:.2f}h")

        # ── Upsert ────────────────────────────────────────────────────── #
        existing = self.db.query(ProcessedAttendance).filter(
            and_(
                ProcessedAttendance.uid   == uid,
                ProcessedAttendance.date  == target_date,
                ProcessedAttendance.shift == shift
            )
        ).first()

        fields = dict(
            first_in               = first_in,
            last_out               = last_out,
            work_duration_hours    = work_duration,
            overtime_hours         = overtime_hours,
            status                 = status,
            is_late                = is_late,
            is_early_leave         = is_early,
            late_by_minutes        = late_by,
            early_leave_by_minutes = early_by,
            total_punches          = len(logs),
            remarks                = "; ".join(remarks) if remarks else None,
        )

        if existing:
            for k, v in fields.items():
                setattr(existing, k, v)
            existing.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(existing)
            return existing

        processed = ProcessedAttendance(uid=uid, date=target_date, shift=shift, **fields)
        self.db.add(processed)
        self.db.commit()
        self.db.refresh(processed)
        return processed

    # ------------------------------------------------------------------ #
    #  Private helpers                                                     #
    # ------------------------------------------------------------------ #

    def _calculate_overtime(
        self,
        last_out: datetime,
        shift: ShiftType,
        work_date: date
    ) -> float:
        """Returns overtime hours beyond shift end. 0 if left before shift end."""
        shift_data  = self.shift_detector.shifts[shift.value]
        shift_start = shift_data["start"]
        shift_end   = shift_data["end"]

        # Night shift end is next calendar day
        if shift_start > shift_end:
            shift_end_dt = datetime.combine(work_date + timedelta(days=1), shift_end)
        else:
            shift_end_dt = datetime.combine(work_date, shift_end)

        seconds = (last_out - shift_end_dt).total_seconds()
        return round(seconds / 3600, 2) if seconds > 0 else 0.0

    def _determine_status(
        self,
        first_in: Optional[datetime],
        last_out: Optional[datetime],
        shift: ShiftType,
        work_duration: Optional[float]
    ) -> AttendanceStatus:
        if not first_in and not last_out:
            return AttendanceStatus.ABSENT
        if not first_in or not last_out:
            return AttendanceStatus.INCOMPLETE

        if work_duration is not None:
            expected = self.shift_detector.get_expected_shift_hours(shift)
            if work_duration < 4 or work_duration < (expected / 2):
                return AttendanceStatus.HALF_DAY

        is_late,  _ = self.shift_detector.calculate_late_minutes(first_in, shift)
        is_early, _ = self.shift_detector.calculate_early_leave_minutes(last_out, shift)

        if is_late:
            return AttendanceStatus.LATE
        if is_early:
            return AttendanceStatus.EARLY_LEAVE
        return AttendanceStatus.PRESENT

    # ------------------------------------------------------------------ #
    #  Public bulk helpers                                                 #
    # ------------------------------------------------------------------ #

    def process_all_pending(self) -> Dict[str, int]:
        pending = self.db.query(
            AttendanceLog.uid,
            func.date(AttendanceLog.timestamp).label("log_date")
        ).distinct().all()

        processed_count = 0
        error_count     = 0
        for uid, log_date in pending:
            try:
                self.process_daily_attendance(uid, log_date)
                processed_count += 1
            except Exception as e:
                print(f"Error processing UID {uid} on {log_date}: {e}")
                error_count += 1

        return {"processed": processed_count, "errors": error_count, "total": len(pending)}

    def process_date_range(self, uid: int, start_date: date, end_date: date):
        results, current = [], start_date
        while current <= end_date:
            rec = self.process_daily_attendance(uid, current)
            if rec:
                results.append(rec)
            current += timedelta(days=1)
        return results

    def get_user_attendance_summary(
        self,
        uid: int,
        start_date: date,
        end_date: date,
        detailed: bool = False
    ) -> Dict:
        records = self.db.query(ProcessedAttendance).filter(
            and_(
                ProcessedAttendance.uid  == uid,
                ProcessedAttendance.date >= start_date,
                ProcessedAttendance.date <= end_date
            )
        ).order_by(ProcessedAttendance.date.asc()).all()

        total_days  = len(records)
        total_hours = sum(r.work_duration_hours or 0 for r in records)
        total_ot    = sum(r.overtime_hours      or 0 for r in records)

        result = {
            "uid": uid,
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "summary": {
                "total_days":            total_days,
                "present":               sum(1 for r in records if r.status == AttendanceStatus.PRESENT),
                "late":                  sum(1 for r in records if r.status == AttendanceStatus.LATE),
                "early_leave":           sum(1 for r in records if r.status == AttendanceStatus.EARLY_LEAVE),
                "half_day":              sum(1 for r in records if r.status == AttendanceStatus.HALF_DAY),
                "incomplete":            sum(1 for r in records if r.status == AttendanceStatus.INCOMPLETE),
                "total_hours_worked":    round(total_hours, 2),
                "total_overtime_hours":  round(total_ot, 2),
                "average_hours_per_day": round(total_hours / total_days, 2) if total_days else 0,
            }
        }

        if detailed:
            from collections import OrderedDict
            months: dict = OrderedDict()
            for r in records:
                key = r.date.strftime("%Y-%m")
                entry = {
                    "date":                   r.date.isoformat(),
                    "shift":                  r.shift.value if r.shift else None,
                    "status":                 r.status.value if r.status else None,
                    "first_in":               r.first_in.isoformat()  if r.first_in  else None,
                    "last_out":               r.last_out.isoformat()  if r.last_out  else None,
                    "work_duration_hours":    r.work_duration_hours,
                    "overtime_hours":         r.overtime_hours,
                    "is_late":                r.is_late,
                    "late_by_minutes":        r.late_by_minutes,
                    "is_early_leave":         r.is_early_leave,
                    "early_leave_by_minutes": r.early_leave_by_minutes,
                    "total_punches":          r.total_punches,
                    "remarks":                r.remarks,
                }
                if key not in months:
                    months[key] = {"month": key, "days": []}
                months[key]["days"].append(entry)

            for m in months.values():
                days = m["days"]
                m["month_summary"] = {
                    "total_days":           len(days),
                    "present":              sum(1 for d in days if d["status"] == "present"),
                    "late":                 sum(1 for d in days if d["status"] == "late"),
                    "incomplete":           sum(1 for d in days if d["status"] == "incomplete"),
                    "total_hours_worked":   round(sum(d["work_duration_hours"] or 0 for d in days), 2),
                    "total_overtime_hours": round(sum(d["overtime_hours"]      or 0 for d in days), 2),
                }

            result["months"] = list(months.values())

        return result