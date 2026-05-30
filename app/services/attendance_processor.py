# app/services/attendance_processor.py
"""
Attendance processor — ESSL F22 hospital edition.

ROOT CAUSE OF JAYAKUMARI'S WRONG TIMES (fixed here)
─────────────────────────────────────────────────────

BUG 1 — Wrong punch type classification:
  Old code: is_in = (punch_type == 0)
  Problem:  ESSL F22 sends punch_type=4 (OVERTIME_IN) for some check-ins.
            The old code treated type 4 as "OUT" (non-zero = out).
            April 3: types=[4,4,0,1] → types 4 were treated as OUT, giving
            wrong session start times.

  Fix: Proper type taxonomy:
    IN  types: 0=CHECKIN, 3=BREAK_IN, 4=OVERTIME_IN
    OUT types: 1=CHECKOUT, 2=BREAK_OUT, 5=OVERTIME_OUT

BUG 2 — Keep LAST of consecutive INs instead of FIRST:
  Old code: when multiple consecutive INs appear, replace with the later one.
  Problem:  April 2 has types=[0,0,0,1] at [11:43, 13:02, 20:08, 22:23].
            Old code kept replacing: 11:43→13:02→20:08. Final IN = 20:08 PM.
            Real check-in was 11:43 AM. Employee showed as working 2.25h instead of 10.67h.

  Fix: For consecutive same-direction punches:
    - Consecutive INs  → keep FIRST (earliest arrival = actual check-in time)
    - Consecutive OUTs → keep LAST  (latest departure = actual check-out time)
    This correctly handles duplicate swipes AND sequential punch patterns.

BUG 3 — Orphan OUT from previous night shift:
  April 1: types=[1,0,1,1] — first punch is type 1 (CHECKOUT from previous night shift).
  Old code: started pairing from this orphan OUT, giving wrong session start.
  Fix: Orphan OUTs (OUT with no preceding IN) are logged as remarks and skipped.

ALSO RETAINED:
  - Logical day window (DAY_START_TIME) for night shift cross-midnight support
  - Correct finalization (not locking past-day records immediately)
  - Gap-based Mode B for devices that send all type=0
"""

import json
import platform
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Optional, Tuple

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.attendance import (
    AttendanceLog,
    ProcessedAttendance,
    AttendanceStatus,
)

settings  = get_settings()
MAX_SESS  = 2
_FINALIZE_GRACE_HOURS = 1

# ── Punch type taxonomy (ESSL F22 / ZK protocol) ──────────────────────────── #
# IN  = employee is entering / starting work
# OUT = employee is leaving / stopping work
_IN_TYPES  = frozenset({0, 3, 4})   # CHECKIN, BREAK_IN, OVERTIME_IN
_OUT_TYPES = frozenset({1, 2, 5})   # CHECKOUT, BREAK_OUT, OVERTIME_OUT

def _is_in_punch(punch_type: int) -> bool:
    """True if this punch type represents an IN (entering) event."""
    # Default unknown types to OUT (safe — avoids inflating hours)
    return punch_type in _IN_TYPES


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
    if platform.system() == "Windows":
        return dt.strftime("%#I:%M %p")
    return dt.strftime("%-I:%M %p")


# ── Mode A: real punch types from device ───────────────────────────────────── #

def _pair_mode_a(
    logs: List[AttendanceLog],
    last_ts: datetime,
) -> Tuple[List[Dict], List[str]]:
    """
    Pair punches when device sends real punch types (not all type=0).

    Algorithm:
    1. Group consecutive punches of the same direction (IN or OUT).
       Uses full punch type taxonomy: {0,3,4}=IN, {1,2,5}=OUT.
    2. From each group:
       - IN group  → keep the FIRST punch (earliest arrival = real check-in time)
       - OUT group → keep the LAST  punch (latest departure = real check-out time)
    3. Pair resulting canonical punches as sessions: IN→OUT, IN→OUT (max 2 sessions).
    4. Orphan OUTs (OUT with no preceding IN, e.g. end of previous night shift)
       are skipped with a remark — not treated as session starts.

    Why FIRST for INs?
      Employees often swipe multiple times if the device is slow.
      The first successful swipe = actual arrival time.
      Keeping the last would push the recorded start time hours later.

    Why LAST for OUTs?
      The last OUT swipe = actual departure time.
      Earlier duplicate OUTs are just accidental re-taps.
    """
    remarks: List[str] = []

    if not logs:
        return [], []

    # Step 1: Build direction-groups of consecutive same-direction punches
    groups: List[Tuple[bool, AttendanceLog]] = []  # (is_in, canonical_log)
    i = 0
    while i < len(logs):
        curr_is_in = _is_in_punch(logs[i].punch_type)
        group: List[AttendanceLog] = [logs[i]]

        j = i + 1
        while j < len(logs) and _is_in_punch(logs[j].punch_type) == curr_is_in:
            group.append(logs[j])
            j += 1

        # Pick canonical punch from group
        if curr_is_in:
            canonical = group[0]    # FIRST IN  = real check-in time
            dropped   = group[1:]
        else:
            canonical = group[-1]   # LAST OUT   = real check-out time
            dropped   = group[:-1]

        direction = "IN" if curr_is_in else "OUT"
        for d in dropped:
            remarks.append(
                f"Duplicate {direction} at {_fmt_time(d.timestamp)}; "
                f"kept {_fmt_time(canonical.timestamp)}"
            )

        groups.append((curr_is_in, canonical))
        i = j

    # Step 2: Pair canonical groups into IN→OUT sessions
    sessions: List[Dict] = []
    j = 0
    while j < len(groups):
        if len(sessions) >= MAX_SESS:
            # Already have max sessions — merge any remaining OUTs into last session's OUT
            remaining_outs = [g[1].timestamp for g in groups[j:] if not g[0]]
            if remaining_outs:
                latest_out = max(remaining_outs)
                if sessions[-1]["out"] and latest_out > sessions[-1]["out"]:
                    remarks.append(
                        f"Extra OUT at {_fmt_time(latest_out)} merged into last session"
                    )
                    sessions[-1]["out"] = latest_out
            break

        curr_is_in, curr_log = groups[j]

        if not curr_is_in:
            # Orphan OUT — no IN precedes it in this logical day.
            # This happens when a night-shift OUT punch lands in the next day's window
            # but the matching IN was in the previous day's window (correct by DAY_START_TIME).
            # OR it's an accidental extra OUT swipe.
            remarks.append(
                f"Orphan OUT at {_fmt_time(curr_log.timestamp)} — no matching IN; skipped"
            )
            j += 1
            continue

        in_ts = curr_log.timestamp

        if j + 1 < len(groups) and not groups[j + 1][0]:
            # Next group is an OUT — pair them
            out_ts = groups[j + 1][1].timestamp
            sessions.append({"in": in_ts, "out": out_ts})
            j += 2
        else:
            # No OUT follows this IN — open session (awaiting checkout)
            remarks.append(
                f"Checkout awaited for {_fmt_time(in_ts)}; using last punch as interim"
            )
            sessions.append({"in": in_ts, "out": None})
            j += 1

    return sessions[:MAX_SESS], remarks


# ── Mode B: all punches are type=0 (gap-based grouping) ───────────────────── #

def _pair_mode_b_gap(
    timestamps: List[datetime],
    last_ts: datetime,
    min_gap_minutes: int,
) -> Tuple[List[Dict], List[str]]:
    """
    Pair punches when all punch_type=0 (device does not send real IN/OUT types).
    Uses time gaps to group duplicate swipes, then pairs alternating IN/OUT.

    Group punches within min_gap_minutes → same event (duplicate swipes).
    Keep the LAST of each group. Pair as IN→OUT→IN→OUT.
    """
    if not timestamps:
        return [], []

    remarks: List[str] = []

    # Group by time gap
    groups: List[List[datetime]] = [[timestamps[0]]]
    for k in range(1, len(timestamps)):
        gap_mins = (timestamps[k] - timestamps[k - 1]).total_seconds() / 60
        if gap_mins <= min_gap_minutes:
            groups[-1].append(timestamps[k])
        else:
            groups.append([timestamps[k]])

    # Keep last of each group; report duplicates
    canonical: List[datetime] = []
    for gi, group in enumerate(groups):
        direction = "IN" if gi % 2 == 0 else "OUT"
        if len(group) > 1:
            for dup in group[:-1]:
                remarks.append(
                    f"Duplicate {direction} at {_fmt_time(dup)}; kept {_fmt_time(group[-1])}"
                )
        canonical.append(group[-1])

    # Pair canonical as IN/OUT sessions
    sessions: List[Dict] = []
    i = 0
    while i < len(canonical):
        if len(sessions) >= MAX_SESS:
            remaining_max = max(canonical[i:])
            if sessions[-1]["out"] and remaining_max > sessions[-1]["out"]:
                remarks.append(f"Extra punches merged into last OUT ({_fmt_time(remaining_max)})")
                sessions[-1]["out"] = remaining_max
            break
        in_ts = canonical[i]
        if i + 1 < len(canonical):
            sessions.append({"in": in_ts, "out": canonical[i + 1]})
            i += 2
        else:
            remarks.append(f"Single punch {_fmt_time(in_ts)}; awaiting checkout")
            sessions.append({"in": in_ts, "out": None})
            i += 1

    return sessions, remarks


# ── Calculation helpers ────────────────────────────────────────────────────── #

def _total_hours(sessions: List[Dict]) -> float:
    total = 0.0
    for s in sessions:
        if s["in"] and s["out"] and s["out"] > s["in"]:
            total += (s["out"] - s["in"]).total_seconds() / 3600
    return round(total, 2)


def _determine_status(hours: float) -> AttendanceStatus:
    if hours <= 0:
        return AttendanceStatus.INCOMPLETE
    if hours >= settings.PRESENT_HOURS:
        return AttendanceStatus.PRESENT
    if hours >= settings.HALF_DAY_HOURS:
        return AttendanceStatus.HALF_DAY
    return AttendanceStatus.INCOMPLETE


def _has_new_punches(db: Session, uid: int, target_date: date, since: datetime) -> bool:
    """True if any punch in the logical day window arrived after `since`."""
    start_dt, end_dt = _day_window(target_date, settings.day_start)
    return (
        db.query(AttendanceLog)
        .filter(
            AttendanceLog.uid == uid,
            AttendanceLog.timestamp >= start_dt,
            AttendanceLog.timestamp <  end_dt,
            AttendanceLog.created_at > since,
        )
        .first() is not None
    )


# ═══════════════════════════════════════════════════════════════════════════ #
#  Main processor                                                              #
# ═══════════════════════════════════════════════════════════════════════════ #

class AttendanceProcessor:

    def __init__(self, db: Session):
        self.db = db

    def process_daily_attendance(
        self,
        uid: int,
        target_date: date,
        force: bool = False,
    ) -> Optional[ProcessedAttendance]:
        """
        Process all punches for uid on the logical workday of target_date.
        Uses DAY_START_TIME to correctly group cross-midnight night shifts.
        """
        day_start        = settings.day_start
        start_dt, end_dt = _day_window(target_date, day_start)

        # Smart skip — already finalized with no new punches
        if not force:
            existing = (
                self.db.query(ProcessedAttendance)
                .filter(ProcessedAttendance.uid == uid, ProcessedAttendance.date == target_date)
                .first()
            )
            if existing and existing.is_finalized:
                if not _has_new_punches(self.db, uid, target_date, existing.updated_at):
                    return existing

        # Fetch logs using logical day window
        logs = (
            self.db.query(AttendanceLog)
            .filter(
                AttendanceLog.uid == uid,
                AttendanceLog.timestamp >= start_dt,
                AttendanceLog.timestamp <  end_dt,
            )
            .order_by(AttendanceLog.timestamp)
            .all()
        )

        if not logs:
            return None

        last_ts = logs[-1].timestamp

        # Choose Mode A or Mode B
        all_type_zero = all(l.punch_type == 0 for l in logs)
        if all_type_zero:
            # Mode B: device doesn't send real IN/OUT types → gap-based
            min_gap  = getattr(settings, "MIN_BREAK_GAP_MINUTES", 30)
            sessions, remarks = _pair_mode_b_gap(
                [l.timestamp for l in logs], last_ts, min_gap
            )
        else:
            # Mode A: device sends real punch types → use proper taxonomy
            sessions, remarks = _pair_mode_a(logs, last_ts)

        # Fill open sessions with last_ts as interim
        has_open   = any(s["out"] is None for s in sessions)
        inferred   = any("awaiting" in r.lower() or "inferred" in r.lower() for r in remarks)
        for s in sessions:
            if s["out"] is None:
                s["out"] = last_ts

        # Calculate hours & status
        total_hrs = _total_hours(sessions)
        ot_hours  = round(max(0.0, total_hrs - settings.PRESENT_HOURS), 2)
        status    = _determine_status(total_hrs)
        if status == AttendanceStatus.PRESENT and ot_hours > 0:
            status = AttendanceStatus.PRESENT_OT
        if ot_hours > 0:
            remarks.append(f"OT: {ot_hours:.2f}h")

        shift_label = "Break Shift" if len(sessions) == 2 else "Regular"

        # Finalize only after the logical day window + grace has fully passed
        grace_end           = end_dt + timedelta(hours=_FINALIZE_GRACE_HOURS)
        day_completely_over = datetime.now() > grace_end
        is_finalized        = (not inferred and not has_open) or day_completely_over

        sessions_json = json.dumps([
            {"in":  s["in"].isoformat()  if s["in"]  else None,
             "out": s["out"].isoformat() if s["out"] else None}
            for s in sessions
        ])

        fields = dict(
            punch_sessions=sessions_json,
            shift=shift_label,
            first_in=sessions[0]["in"]   if sessions else None,
            last_out=sessions[-1]["out"]  if sessions else None,
            work_duration_hours=total_hrs,
            overtime_hours=ot_hours,
            status=status,
            total_punches=len(logs),
            remarks="; ".join(remarks) if remarks else None,
            is_finalized=is_finalized,
            is_late=False, is_early_leave=False,
            late_by_minutes=0, early_leave_by_minutes=0,
        )

        existing = (
            self.db.query(ProcessedAttendance)
            .filter(ProcessedAttendance.uid == uid, ProcessedAttendance.date == target_date)
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

    def process_all_pending(
        self,
        force: bool = False,
        since_days: Optional[int] = None,
    ) -> Dict:
        """
        Process uid+logical_date pairs that need processing.
        since_days: limit log scan to last N days (use 2 for routine syncs).
        """
        day_start  = settings.day_start
        log_query  = self.db.query(AttendanceLog.uid, AttendanceLog.timestamp)
        if since_days is not None:
            cutoff = datetime.now() - timedelta(days=since_days)
            log_query = log_query.filter(AttendanceLog.timestamp >= cutoff)

        pairs = set()
        for uid, ts in log_query.all():
            pairs.add((uid, _logical_date(ts, day_start)))

        processed_lookup = {(p.uid, p.date): p for p in self.db.query(ProcessedAttendance).all()}

        ok = skipped = err = 0
        to_process = []
        for uid, log_date in pairs:
            p = processed_lookup.get((uid, log_date))
            if force or p is None or not p.is_finalized:
                to_process.append((uid, log_date))
            elif _has_new_punches(self.db, uid, log_date, p.updated_at):
                to_process.append((uid, log_date))
            else:
                skipped += 1

        for uid, log_date in to_process:
            try:
                self.process_daily_attendance(uid, log_date, force=True)
                ok += 1
            except Exception as e:
                print(f"❌ Error processing UID {uid} on {log_date}: {e}")
                err += 1

        print(f"📊 Processing — Total: {len(pairs)}, Done: {ok}, Skipped: {skipped}, Errors: {err}")
        return {"total": len(pairs), "processed": ok, "skipped": skipped, "errors": err}

    def process_date_range(self, uid: int, start: date, end: date) -> List:
        results, current = [], start
        while current <= end:
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
        total_ot    = sum(r.overtime_hours or 0 for r in records)

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
                    try: sessions_raw = json.loads(r.punch_sessions)
                    except: pass
                entry = {
                    "date": r.date.isoformat(), "sessions": sessions_raw,
                    "shift": r.shift or "Regular",
                    "first_in": r.first_in.isoformat() if r.first_in else None,
                    "last_out": r.last_out.isoformat() if r.last_out else None,
                    "work_duration_hours": r.work_duration_hours,
                    "overtime_hours": r.overtime_hours or 0,
                    "status": r.status.value if r.status else None,
                    "total_punches": r.total_punches,
                    "remarks": r.remarks,
                }
                if key not in months:
                    months[key] = {"month": key, "days": []}
                months[key]["days"].append(entry)

            for m in months.values():
                days = m["days"]
                m["month_summary"] = {
                    "total_days": len(days),
                    "present":    sum(1 for d in days if d["status"] in ("present","present_ot")),
                    "half_day":   sum(1 for d in days if d["status"] == "half_day"),
                    "incomplete": sum(1 for d in days if d["status"] == "incomplete"),
                    "absent":     sum(1 for d in days if d["status"] == "absent"),
                    "total_hours_worked":   round(sum(d["work_duration_hours"] or 0 for d in days),2),
                    "total_overtime_hours": round(sum(d["overtime_hours"] or 0 for d in days),2),
                }
            result["months"] = list(months.values())
        return result