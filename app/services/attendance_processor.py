# app/services/attendance_processor.py
"""
Flexible 24-hour attendance processor.

Business Rules
──────────────
1.  A "logical work-day" is defined by DAY_START_TIME in .env.
    e.g. DAY_START_TIME=04:00 → day runs 04:00 today to 03:59 next day.
    Punches are queried by CALENDAR date (the date column on AttendanceLogs),
    but cross-midnight work is handled correctly because we always compare
    datetimes, not times.

2.  Maximum 2 sessions per day:
      Session 1  —  first IN  → first OUT
      Session 2  —  second IN → second OUT   (optional, "Break Shift")
    There is no fixed break duration.  An employee may work 3 h in the
    morning and 6 h in the evening, or 9 h non-stop.  Both are fine.

3.  Illiterate employees / accidental duplicate taps:
    An employee might tap the same finger twice in a row (double-IN or
    double-OUT).  Rule: KEEP THE LAST duplicate, discard earlier ones.
    This is applied before session pairing in Mode A and Mode B.

4.  Punch modes:
    Mode A — device sends 0 = IN, non-0 = OUT (proper alternation).
    Mode B — F22 quirk: every punch arrives as type 0.
              Interpret by ordinal position: 1st=IN, 2nd=OUT, 3rd=IN, 4th=OUT.
              5+ punches: treat first 2 as session 1, rest collapse to
              session 2 (IN=3rd punch, OUT=last punch).

5.  Missing checkout:
    ANY unclosed session always gets OUT = last recorded timestamp of the day.
    Remark is added: "Checkout inferred from last punch (HH:MM)".

6.  Status thresholds:
      total_hours >= PRESENT_HOURS  → present (or present_ot if OT > 0)
      total_hours >= HALF_DAY_HOURS → half_day
      total_hours >  0              → incomplete
      no punches                    → absent
"""

import json
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.attendance import (
    AttendanceLog,
    ProcessedAttendance,
    AttendanceStatus,
)

settings   = get_settings()
MAX_SESS   = 2   # hard cap — never more than 2 sessions per day


# ═══════════════════════════════════════════════════════════════════════════ #
#  Internal helpers                                                            #
# ═══════════════════════════════════════════════════════════════════════════ #

def _dedup_consecutive(timestamps: List[datetime]) -> Tuple[List[datetime], List[str]]:
    """
    Remove consecutive duplicate taps (illiterate-employee protection).

    Algorithm:
      Walk the sorted timestamp list and track the "expected" next direction
      (IN or OUT, alternating).  If the same direction appears twice in a row,
      DISCARD the earlier one and keep the later one.  Collect a remark for
      every discarded punch.

    Returns:
      cleaned  — deduplicated list of timestamps (max 4: IN OUT IN OUT)
      remarks  — list of human-readable notes about what was discarded
    """
    remarks: List[str] = []
    cleaned: List[datetime] = []

    # We process in pairs: odd positions = IN, even positions = OUT
    # Build groups of consecutive same-direction punches first.
    # Since Mode B is all-0, "direction" is determined by position parity.
    # For Mode A we do the same but use punch_type later.
    # Here we only handle the TIMESTAMP list (direction already resolved).
    # Simply: if the next timestamp would be same direction as previous,
    # replace previous with the later one.

    # We do a forward pass keeping track of last kept ts per slot.
    # Slots: 0=IN1, 1=OUT1, 2=IN2, 3=OUT2
    slots: List[Optional[datetime]] = [None, None, None, None]
    slot  = 0

    for ts in timestamps:
        if slot >= 4:
            # More than 4 punches: fold into last slot, keeping latest
            prev = slots[3]
            if prev is not None and ts > prev:
                remarks.append(
                    f"Extra punch at {ts.strftime('%H:%M')} collapsed into session-2 OUT"
                )
                slots[3] = ts
            continue

        if slots[slot] is None:
            slots[slot] = ts
        else:
            # Duplicate in the same slot → keep the later timestamp
            remarks.append(
                f"Duplicate {'IN' if slot%2==0 else 'OUT'} at "
                f"{slots[slot].strftime('%H:%M')}; "
                f"replaced with {ts.strftime('%H:%M')}"
            )
            slots[slot] = ts
            continue

        slot += 1

    cleaned = [s for s in slots if s is not None]
    return cleaned, remarks


def _pair_mode_a(
    logs: List[AttendanceLog],
    last_ts: datetime,
) -> Tuple[List[Dict], List[str]]:
    """
    Mode A: device sends real punch_type (0=IN, non-0=OUT).

    Consecutive same-type punches → keep the LAST one (discard earlier).
    Returns (sessions, remarks).
    """
    remarks: List[str] = []
    # Walk logs, deduplicate consecutive same-direction punches
    clean_logs: List[AttendanceLog] = []
    for log in logs:
        if clean_logs and (log.punch_type == 0) == (clean_logs[-1].punch_type == 0):
            # Same direction as previous → discard previous, keep this (later) one
            direction = "IN" if log.punch_type == 0 else "OUT"
            remarks.append(
                f"Duplicate {direction} at {clean_logs[-1].timestamp.strftime('%H:%M')}; "
                f"replaced by {log.timestamp.strftime('%H:%M')}"
            )
            clean_logs[-1] = log
        else:
            clean_logs.append(log)

    # Now pair IN→OUT
    sessions: List[Dict] = []
    current_in: Optional[datetime] = None

    for log in clean_logs:
        if log.punch_type == 0:      # IN
            if current_in is None:
                current_in = log.timestamp
        else:                        # OUT
            if current_in is not None:
                sessions.append({"in": current_in, "out": log.timestamp})
                current_in = None
            # OUT without prior IN → ignore

    # Unclosed session
    if current_in is not None:
        remarks.append(f"Checkout inferred from last punch ({last_ts.strftime('%H:%M')})")
        sessions.append({"in": current_in, "out": last_ts})

    return sessions[:MAX_SESS], remarks


def _pair_mode_b(
    timestamps: List[datetime],
    last_ts: datetime,
) -> Tuple[List[Dict], List[str]]:
    """
    Mode B: F22 sends all punches as type-0.
    Interpret by ordinal: 1st=IN, 2nd=OUT, 3rd=IN, 4th=OUT.
    Extra punches (5+): collapse into session-2 OUT = last timestamp.

    Deduplication: consecutive same-slot taps (e.g. two accidental IN taps)
    → keep the LAST one and add a remark.
    """
    clean, remarks = _dedup_consecutive(timestamps)
    n = len(clean)

    sessions: List[Dict] = []

    if n == 1:
        # Single punch, no OUT → 0-hour record; infer OUT = that same punch
        remarks.append(f"Only one punch ({clean[0].strftime('%H:%M')}); checkout inferred")
        sessions = [{"in": clean[0], "out": clean[0]}]

    elif n == 2:
        sessions = [{"in": clean[0], "out": clean[1]}]

    elif n == 3:
        # Session 1: clean[0] → clean[1]
        # Session 2: clean[2] → last_ts (inferred OUT)
        remarks.append(f"Checkout inferred from last punch ({last_ts.strftime('%H:%M')})")
        sessions = [
            {"in": clean[0], "out": clean[1]},
            {"in": clean[2], "out": last_ts},
        ]

    else:
        # n >= 4: two proper sessions
        sessions = [
            {"in": clean[0], "out": clean[1]},
            {"in": clean[2], "out": clean[3]},
        ]

    return sessions, remarks


def _total_hours(sessions: List[Dict]) -> float:
    total = 0.0
    for s in sessions:
        if s["in"] and s["out"] and s["out"] > s["in"]:
            total += (s["out"] - s["in"]).total_seconds() / 3600
    return round(total, 2)


def _determine_status(hours: float, has_punches: bool) -> AttendanceStatus:
    if not has_punches:
        return AttendanceStatus.ABSENT
    if hours <= 0:
        return AttendanceStatus.INCOMPLETE
    if hours >= settings.PRESENT_HOURS:
        return AttendanceStatus.PRESENT   # OT flag added later
    if hours >= settings.HALF_DAY_HOURS:
        return AttendanceStatus.HALF_DAY
    return AttendanceStatus.INCOMPLETE


# ═══════════════════════════════════════════════════════════════════════════ #
#  Main processor class                                                        #
# ═══════════════════════════════════════════════════════════════════════════ #

class AttendanceProcessor:

    def __init__(self, db: Session):
        self.db = db

    # ── Per-day ─────────────────────────────────────────────────────────── #

    def process_daily_attendance(
        self,
        uid: int,
        target_date: date,
    ) -> Optional[ProcessedAttendance]:
        """
        Process all punches for `uid` on `target_date` (calendar date).
        """
        logs = (
            self.db.query(AttendanceLog)
            .filter(
                and_(
                    AttendanceLog.uid == uid,
                    func.date(AttendanceLog.timestamp) == target_date,
                )
            )
            .order_by(AttendanceLog.timestamp)
            .all()
        )

        if not logs:
            return None

        sorted_ts = [l.timestamp for l in logs]
        last_ts   = sorted_ts[-1]

        all_in_mode = all(l.punch_type == 0 for l in logs)

        if all_in_mode:
            sessions, remarks = _pair_mode_b(sorted_ts, last_ts)
        else:
            sessions, remarks = _pair_mode_a(logs, last_ts)

        total_hrs = _total_hours(sessions)
        ot_hours  = round(max(0.0, total_hrs - settings.PRESENT_HOURS), 2)
        status    = _determine_status(total_hrs, has_punches=True)

        if status == AttendanceStatus.PRESENT and ot_hours > 0:
            status = AttendanceStatus.PRESENT_OT

        if ot_hours > 0:
            remarks.append(f"OT: {ot_hours:.2f}h")

        shift_label = "Break Shift" if len(sessions) == 2 else "Regular"

        sessions_json = json.dumps([
            {
                "in":  s["in"].isoformat()  if s["in"]  else None,
                "out": s["out"].isoformat() if s["out"] else None,
            }
            for s in sessions
        ])

        fields = dict(
            punch_sessions         = sessions_json,
            shift                  = shift_label,
            first_in               = sessions[0]["in"]  if sessions else None,
            last_out               = sessions[-1]["out"] if sessions else None,
            work_duration_hours    = total_hrs,
            overtime_hours         = ot_hours,
            status                 = status,
            total_punches          = len(logs),
            remarks                = "; ".join(remarks) if remarks else None,
            is_late                = False,
            is_early_leave         = False,
            late_by_minutes        = 0,
            early_leave_by_minutes = 0,
        )

        existing = (
            self.db.query(ProcessedAttendance)
            .filter(
                ProcessedAttendance.uid  == uid,
                ProcessedAttendance.date == target_date,
            )
            .first()
        )

        if existing:
            for k, v in fields.items():
                setattr(existing, k, v)
            existing.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(existing)
            return existing

        record = ProcessedAttendance(uid=uid, date=target_date, **fields)
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    # ── Bulk helpers ─────────────────────────────────────────────────────── #

    def process_all_pending(self) -> Dict:
        pending = (
            self.db.query(
                AttendanceLog.uid,
                func.date(AttendanceLog.timestamp).label("log_date"),
            )
            .distinct()
            .all()
        )
        ok = err = 0
        for uid, log_date in pending:
            try:
                self.process_daily_attendance(uid, log_date)
                ok += 1
            except Exception as e:
                print(f"Error UID {uid} on {log_date}: {e}")
                err += 1
        return {"processed": ok, "errors": err, "total": len(pending)}

    def process_date_range(self, uid: int, start: date, end: date):
        results, current = [], start
        while current <= end:
            rec = self.process_daily_attendance(uid, current)
            if rec:
                results.append(rec)
            current += timedelta(days=1)
        return results

    # ── Summary (used by attendance route & CSV export) ───────────────────── #

    def get_user_attendance_summary(
        self,
        uid: int,
        start_date: date,
        end_date: date,
        detailed: bool = False,
    ) -> Dict:
        records = (
            self.db.query(ProcessedAttendance)
            .filter(
                ProcessedAttendance.uid  == uid,
                ProcessedAttendance.date >= start_date,
                ProcessedAttendance.date <= end_date,
            )
            .order_by(ProcessedAttendance.date.asc())
            .all()
        )

        total_days  = len(records)
        total_hours = sum(r.work_duration_hours or 0 for r in records)
        total_ot    = sum(r.overtime_hours      or 0 for r in records)

        result = {
            "uid": uid,
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "summary": {
                "total_days":            total_days,
                "present":               sum(1 for r in records if r.status == AttendanceStatus.PRESENT),
                "present_ot":            sum(1 for r in records if r.status == AttendanceStatus.PRESENT_OT),
                "half_day":              sum(1 for r in records if r.status == AttendanceStatus.HALF_DAY),
                "incomplete":            sum(1 for r in records if r.status == AttendanceStatus.INCOMPLETE),
                "absent":                sum(1 for r in records if r.status == AttendanceStatus.ABSENT),
                "lop":                   sum(1 for r in records if r.status == AttendanceStatus.LOP),
                "total_hours_worked":    round(total_hours, 2),
                "total_overtime_hours":  round(total_ot, 2),
                "average_hours_per_day": round(total_hours / total_days, 2) if total_days else 0,
            },
        }

        if detailed:
            from collections import OrderedDict
            months: dict = OrderedDict()

            for r in records:
                key = r.date.strftime("%Y-%m")
                sessions_raw = []
                if r.punch_sessions:
                    try:
                        sessions_raw = json.loads(r.punch_sessions)
                    except Exception:
                        pass

                entry = {
                    "date":                r.date.isoformat(),
                    "sessions":            sessions_raw,
                    "shift":               r.shift or "Regular",
                    "first_in":            r.first_in.isoformat()  if r.first_in  else None,
                    "last_out":            r.last_out.isoformat()  if r.last_out  else None,
                    "work_duration_hours": r.work_duration_hours,
                    "overtime_hours":      r.overtime_hours or 0,
                    "status":              r.status.value if r.status else None,
                    "total_punches":       r.total_punches,
                    "remarks":             r.remarks,
                }

                if key not in months:
                    months[key] = {"month": key, "days": []}
                months[key]["days"].append(entry)

            for m in months.values():
                days = m["days"]
                m["month_summary"] = {
                    "total_days":           len(days),
                    "present":              sum(1 for d in days if d["status"] in ("present", "present_ot")),
                    "present_ot":           sum(1 for d in days if d["status"] == "present_ot"),
                    "half_day":             sum(1 for d in days if d["status"] == "half_day"),
                    "incomplete":           sum(1 for d in days if d["status"] == "incomplete"),
                    "absent":               sum(1 for d in days if d["status"] == "absent"),
                    "total_hours_worked":   round(sum(d["work_duration_hours"] or 0 for d in days), 2),
                    "total_overtime_hours": round(sum(d["overtime_hours"]      or 0 for d in days), 2),
                }

            result["months"] = list(months.values())

        return result