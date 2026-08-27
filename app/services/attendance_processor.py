# app/services/attendance_processor.py
"""
Dual-Device Attendance Processor with Regular/Break Shift Support
────────────────────────────────────────────────────────────────────────────────

ARCHITECTURE:
  • Device 1 (192.168.1.201) → ALL punches = IN  (ignoring punch_type)
  • Device 2 (192.168.1.35)  → ALL punches = OUT (ignoring punch_type)
  • Two modes supported:
    1. REGULAR MODE:  1 IN + 1 OUT = full work session
    2. BREAK SHIFT MODE: 2 IN + 2 OUT = two sessions with break

LOGIC:
  - Sort punches by timestamp
  - Device 1 punches = IN regardless of punch_type
  - Device 2 punches = OUT regardless of punch_type
  - Latest punch from same device wins (handles duplicate swipes)
  - Pair chronologically: IN→OUT, IN→OUT

SHIFT DETECTION:
  • If 1 IN + 1 OUT → Regular shift
  • If 2 IN + 2 OUT → Break shift (with break between)
  • punch_sessions field stores JSON: [{"in": ISO, "out": ISO}, ...]

STATUS CALCULATION (Updated):
  • If at least ONE complete session (IN + OUT) exists:
    - PRESENT:    >= 9.0 hours total work
    - HALF_DAY:   >= 4.5 hours and < 9.0 hours
    - INCOMPLETE: < 4.5 hours (but has complete session)
  • INCOMPLETE: Has IN punch but no complete session (missing OUT)
  • ABSENT:     No punches at all
"""

import json
import platform
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.config import get_settings
from app.models.attendance import (
    AttendanceLog,
    ProcessedAttendance,
    AttendanceStatus,
)
from app.models.user import User

settings = get_settings()
MAX_SESSIONS = 2
_FINALIZE_GRACE_HOURS = 1


# ── Logical day helpers ────────────────────────────────────────────────────── #

def _logical_date(ts: datetime, day_start: time) -> date:
    """Punches before DAY_START_TIME belong to the PREVIOUS day's workday."""
    if ts.time() < day_start:
        return (ts - timedelta(days=1)).date()
    return ts.date()


def _day_window(logical_date: date, day_start: time) -> Tuple[datetime, datetime]:
    """All punches in [start, end) belong to this logical workday."""
    start = datetime.combine(logical_date, day_start)
    end   = datetime.combine(logical_date + timedelta(days=1), day_start)
    return start, end


# ── Time formatting ────────────────────────────────────────────────────────── #

def _fmt_time(dt: datetime) -> str:
    """Format datetime as 12-hour time with AM/PM."""
    if platform.system() == "Windows":
        return dt.strftime("%#I:%M %p")
    return dt.strftime("%-I:%M %p")


# ── Dual-device pairing logic ──────────────────────────────────────────────── #

def _pair_dual_device(
    logs: List[AttendanceLog],
    device_1_ip: str,
    device_2_ip: str,
) -> Tuple[List[Dict], List[str]]:
    """
    Pair punches from dual devices into sessions.

    Algorithm:
    1. Separate logs by device:
       - Device 1 (device_1_ip) = IN punches
       - Device 2 (device_2_ip) = OUT punches
    2. For each device, if multiple punches at same "moment" (within 2 min),
       keep only the LATEST (handles duplicate swipes)
    3. Pair chronologically: IN → OUT, IN → OUT (max 2 sessions)

    Returns:
        (sessions, remarks)
        sessions: List of {"in": datetime, "out": datetime or None}
        remarks: List of processing notes
    """
    if not logs:
        return [], []

    remarks: List[str] = []

    # Separate by device
    in_punches  = [log for log in logs if log.device_ip == device_1_ip]
    out_punches = [log for log in logs if log.device_ip == device_2_ip]

    # Sort by timestamp
    in_punches.sort(key=lambda x: x.timestamp)
    out_punches.sort(key=lambda x: x.timestamp)

    # Deduplicate: keep latest punch within 2-minute window
    def dedupe_punches(punches: List[AttendanceLog]) -> List[datetime]:
        """Keep latest punch within 2-minute duplicates."""
        if not punches:
            return []

        result = []
        i = 0
        while i < len(punches):
            current = punches[i]
            j = i + 1

            # Find all punches within 2 minutes
            while j < len(punches):
                if (punches[j].timestamp - current.timestamp).total_seconds() <= 120:
                    j += 1
                else:
                    break

            # Keep the latest punch in this group
            latest = punches[j - 1]
            result.append(latest.timestamp)

            if j - i > 1:
                remarks.append(
                    f"Merged {j - i} duplicate punches around {_fmt_time(latest.timestamp)}"
                )

            i = j

        return result

    in_times  = dedupe_punches(in_punches)
    out_times = dedupe_punches(out_punches)

    # Pair IN and OUT chronologically
    sessions: List[Dict] = []
    orphan_out_times: List[datetime] = []
    in_idx  = 0
    out_idx = 0

    while in_idx < len(in_times) and len(sessions) < MAX_SESSIONS:
        in_time = in_times[in_idx]

        # Find the next OUT after this IN
        out_time = None
        while out_idx < len(out_times):
            if out_times[out_idx] > in_time:
                out_time = out_times[out_idx]
                out_idx += 1
                break
            else:
                # Orphan OUT before this IN - preserve it for the report
                remarks.append(f"Orphan OUT at {_fmt_time(out_times[out_idx])} — skipped")
                orphan_out_times.append(out_times[out_idx])
                out_idx += 1

        sessions.append({"in": in_time, "out": out_time})
        in_idx += 1

    # Handle remaining unpaired INs
    while in_idx < len(in_times) and len(sessions) < MAX_SESSIONS:
        remarks.append(f"No OUT found for IN at {_fmt_time(in_times[in_idx])}")
        sessions.append({"in": in_times[in_idx], "out": None})
        in_idx += 1

    # Note about extra punches
    if in_idx < len(in_times):
        remarks.append(f"{len(in_times) - in_idx} extra IN punches ignored (max 2 sessions)")

    for orphan_out in orphan_out_times:
        for session in sessions:
            if session["out"] is None:
                session["out"] = orphan_out
                break

    return sessions, remarks


# ── Session analysis ───────────────────────────────────────────────────────── #

def _analyze_sessions(sessions: List[Dict]) -> Tuple[Optional[datetime], Optional[datetime], float, str]:
    """
    Analyze sessions to determine:
    - first_in: earliest IN time
    - last_out: latest OUT time
    - total_hours: sum of session durations
    - shift_type: "Regular" or "Break Shift"

    Returns:
        (first_in, last_out, total_hours, shift_type)
    """
    if not sessions:
        return None, None, 0.0, "Regular"

    first_in = sessions[0]["in"]
    last_out = None
    total_hours = 0.0

    for session in sessions:
        if session["out"] and session["out"] > session["in"]:
            last_out = session["out"]
            duration = (session["out"] - session["in"]).total_seconds() / 3600
            total_hours += duration

    # Determine shift type
    if len(sessions) == 1:
        shift_type = "Regular"
    elif len(sessions) == 2:
        shift_type = "Break Shift"
    else:
        shift_type = "Regular"

    return first_in, last_out, total_hours, shift_type


# ── Status determination ───────────────────────────────────────────────────── #

def _determine_status(
    total_hours: float,
    first_in: Optional[datetime],
    last_out: Optional[datetime],
    sessions: List[Dict],
) -> AttendanceStatus:
    """
    Determine attendance status based on work hours.

    NEW Rules (Changed):
    - If at least ONE complete session (IN + OUT) exists:
      - PRESENT:    >= 9.0 hours
      - HALF_DAY:   >= 4.5 hours and < 9.0 hours
      - INCOMPLETE: < 4.5 hours but has complete session
    - INCOMPLETE: Has IN but no complete session (no OUT yet)
    - ABSENT:     No punches (handled outside this function)
    """
    if not first_in:
        return AttendanceStatus.INCOMPLETE

    # Check if at least one session is complete (has both IN and OUT)
    has_complete_session = any(s.get("in") and s.get("out") for s in sessions)

    if not has_complete_session:
        # Has IN punch but no complete session yet
        return AttendanceStatus.INCOMPLETE

    # At least one session is complete - determine status by hours
    if total_hours >= settings.PRESENT_HOURS:
        return AttendanceStatus.PRESENT
    elif total_hours >= settings.HALF_DAY_HOURS:
        return AttendanceStatus.HALF_DAY
    else:
        # Has complete session but less than half day hours
        return AttendanceStatus.INCOMPLETE


# ── Main processor class ───────────────────────────────────────────────────── #

class AttendanceProcessor:
    """
    Process raw attendance logs into processed attendance records.

    Supports dual-device setup:
    - Device 1: IN device
    - Device 2: OUT device

    Supports two modes:
    - Regular: 1 IN + 1 OUT
    - Break Shift: 2 IN + 2 OUT
    """

    def __init__(self, db: Session):
        self.db          = db
        self.day_start   = settings.day_start
        self.device_1_ip = settings.DEVICE_1_IP
        self.device_2_ip = settings.DEVICE_2_IP

    def process_user_date(self, uid: int, target_date: date) -> Dict:
        """
        Process attendance for a specific user and date.

        Args:
            uid: User UID
            target_date: Date to process (logical date)

        Returns:
            Dict with processing results
        """
        start_ts, end_ts = _day_window(target_date, self.day_start)

        # Fetch all logs for this user in the day window
        logs = (
            self.db.query(AttendanceLog)
            .filter(
                AttendanceLog.uid == uid,
                AttendanceLog.timestamp >= start_ts,
                AttendanceLog.timestamp < end_ts,
            )
            .order_by(AttendanceLog.timestamp)
            .all()
        )

        # If there are no logs for the requested day, do not create a blank/absent
        # record for the current day. This lets today's punches be processed once
        # they arrive and avoids hiding real attendance data.
        if not logs:
            return {"status": "no_punches", "date": target_date, "uid": uid}

        # Pair punches into sessions
        sessions, remarks = _pair_dual_device(logs, self.device_1_ip, self.device_2_ip)

        # Analyze sessions
        first_in, last_out, total_hours, shift_type = _analyze_sessions(sessions)

        # Determine status
        status = _determine_status(total_hours, first_in, last_out, sessions)

        # Serialize sessions to JSON
        sessions_json = json.dumps([
            {
                "in": s["in"].isoformat() if s["in"] else None,
                "out": s["out"].isoformat() if s["out"] else None,
            }
            for s in sessions
        ])

        # Check if record exists
        existing = self.db.query(ProcessedAttendance).filter(
            ProcessedAttendance.uid == uid,
            ProcessedAttendance.date == target_date,
        ).first()

        if existing:
            # Update existing record
            existing.shift               = shift_type
            existing.first_in            = first_in
            existing.last_out            = last_out
            existing.work_duration_hours = total_hours
            existing.total_punches       = len(logs)
            existing.status              = status
            existing.punch_sessions      = sessions_json
            existing.remarks             = " | ".join(remarks) if remarks else None
            existing.updated_at          = datetime.utcnow()

            # Finalization check
            if last_out and (datetime.utcnow() - last_out).total_seconds() > _FINALIZE_GRACE_HOURS * 3600:
                existing.is_finalized = True

            self.db.commit()
            return {"status": "updated", "date": target_date, "uid": uid}
        else:
            # Create new record
            new_record = ProcessedAttendance(
                uid                  = uid,
                date                 = target_date,
                shift                = shift_type,
                first_in             = first_in,
                last_out             = last_out,
                work_duration_hours  = total_hours,
                total_punches        = len(logs),
                status               = status,
                punch_sessions       = sessions_json,
                remarks              = " | ".join(remarks) if remarks else None,
                is_finalized         = False,
            )
            self.db.add(new_record)
            self.db.commit()
            return {"status": "created", "date": target_date, "uid": uid}

    def process_all_pending(self) -> Dict:
        """
        Process all pending attendance records.

        Logic:
        - Find all dates with unprocessed logs
        - Process each user-date combination
        - Return statistics

        Returns:
            Dict with processing statistics
        """
        try:
            # Find all unique (uid, date) combinations with logs
            # but either no processed record OR not finalized
            logs_query = (
                self.db.query(
                    AttendanceLog.uid,
                    AttendanceLog.timestamp,
                )
                .all()
            )

            # Build set of (uid, logical_date) needing processing
            to_process = set()
            for log in logs_query:
                logical_dt = _logical_date(log.timestamp, self.day_start)
                to_process.add((log.uid, logical_dt))

            # Filter out finalized records
            finalized = set()
            for uid, dt in to_process:
                existing = self.db.query(ProcessedAttendance).filter(
                    ProcessedAttendance.uid == uid,
                    ProcessedAttendance.date == dt,
                    ProcessedAttendance.is_finalized == True,
                ).first()
                if existing:
                    finalized.add((uid, dt))

            to_process -= finalized

            processed_count = 0
            error_count     = 0

            for uid, logical_dt in to_process:
                try:
                    self.process_user_date(uid, logical_dt)
                    processed_count += 1
                except Exception as e:
                    print(f"❌ Error processing UID {uid}, date {logical_dt}: {e}")
                    error_count += 1

            return {
                "processed": processed_count,
                "errors":    error_count,
                "total":     len(to_process),
            }

        except Exception as e:
            print(f"❌ Error in process_all_pending: {e}")
            return {"processed": 0, "errors": 1, "total": 0}
