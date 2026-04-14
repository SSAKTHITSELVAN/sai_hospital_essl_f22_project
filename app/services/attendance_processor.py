# app/services/attendance_processor.py
"""
Flexible 24-hour attendance processor.

Business Rules
──────────────
1.  No fixed shifts.  Status is determined purely by total hours worked.

2.  Maximum 2 sessions per day:
      Regular:     1 IN + 1 OUT  (single continuous stretch)
      Break Shift: 2 IN + 2 OUT  (e.g. morning + evening, any split)
    No mandatory break duration.  Total = 9 h either way.

3.  Illiterate / accidental duplicate taps:
    If the same direction (IN or IN, OUT or OUT) appears consecutively,
    DISCARD the earlier one, KEEP the later one, add a remark.

4.  Punch modes:
    Mode A — device sends 0=IN / non-0=OUT properly.
    Mode B — F22 quirk: all punches arrive as type 0.
              Interpret by ordinal: 1st=IN1, 2nd=OUT1, 3rd=IN2, 4th=OUT2.
              5+ → session-2 OUT = last timestamp.

5.  Missing checkout:
    Any unclosed session gets OUT = last timestamp of the day. Remark added.

6.  Status thresholds (from .env):
      >= PRESENT_HOURS  → present (or present_ot if OT > 0)
      >= HALF_DAY_HOURS → half_day
      > 0               → incomplete
      no punches        → absent

7.  Smart skip (performance):
    A processed record marked is_finalized=True is skipped unless new raw
    punches have arrived after its updated_at timestamp.
    A day is finalized when:
      - There is a valid last_out  AND
      - No new AttendanceLogs for that uid+date exist after updated_at.
"""

import json
import platform
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

settings = get_settings()
MAX_SESS = 2


# ── Time formatting (cross-platform) ───────────────────────────────────────── #

def _fmt_time(dt: datetime) -> str:
    """Format datetime to '9:30 AM' on all platforms (Windows + Linux)."""
    if platform.system() == "Windows":
        # Windows doesn't support %-I; use %#I instead
        return dt.strftime("%#I:%M %p")
    return dt.strftime("%-I:%M %p")


# ── Punch deduplication ────────────────────────────────────────────────────── #

def _dedup_consecutive_mode_b(
    timestamps: List[datetime],
) -> Tuple[List[datetime], List[str]]:
    """
    For Mode B (all-IN device), deduplicate consecutive same-slot taps.
    Slots: 0=IN1, 1=OUT1, 2=IN2, 3=OUT2.
    If a slot receives more than one tap → keep the LAST one, add remark.
    Any punches beyond slot 3 are collapsed into slot 3 (OUT2 = latest ts).
    """
    remarks: List[str] = []
    slots: List[Optional[datetime]] = [None, None, None, None]
    slot = 0

    for ts in timestamps:
        if slot >= 4:
            # Extra punch: collapse to last slot, keep latest
            if slots[3] is not None and ts > slots[3]:
                remarks.append(
                    f"Extra punch at {_fmt_time(ts)} merged into Session-2 OUT"
                )
                slots[3] = ts
            continue

        direction = "IN" if slot % 2 == 0 else "OUT"

        if slots[slot] is None:
            slots[slot] = ts
        else:
            # Duplicate in same slot → keep the later one
            remarks.append(
                f"Duplicate {direction} ({_fmt_time(slots[slot])}); "
                f"replaced by {_fmt_time(ts)}"
            )
            slots[slot] = ts
            continue   # do NOT advance slot — still filling same slot

        slot += 1

    return [s for s in slots if s is not None], remarks


# ── Mode A pairing ─────────────────────────────────────────────────────────── #

def _pair_mode_a(
    logs: List[AttendanceLog],
    last_ts: datetime,
) -> Tuple[List[Dict], List[str]]:
    """
    Mode A: device sends real punch_type (0=IN, non-0=OUT).
    Consecutive same-direction taps → keep the LAST one.
    """
    remarks: List[str] = []
    clean: List[AttendanceLog] = []

    for log in logs:
        is_in = (log.punch_type == 0)
        if clean:
            prev_is_in = (clean[-1].punch_type == 0)
            if is_in == prev_is_in:
                direction = "IN" if is_in else "OUT"
                remarks.append(
                    f"Duplicate {direction} at {_fmt_time(clean[-1].timestamp)}; "
                    f"replaced by {_fmt_time(log.timestamp)}"
                )
                clean[-1] = log   # replace with later tap
                continue
        clean.append(log)

    sessions: List[Dict] = []
    current_in: Optional[datetime] = None

    for log in clean:
        if log.punch_type == 0:
            if current_in is None:
                current_in = log.timestamp
        else:
            if current_in is not None:
                sessions.append({"in": current_in, "out": log.timestamp})
                current_in = None

    if current_in is not None:
        remarks.append(f"Checkout inferred from last punch ({_fmt_time(last_ts)})")
        sessions.append({"in": current_in, "out": last_ts})

    return sessions[:MAX_SESS], remarks


# ── Mode B pairing ─────────────────────────────────────────────────────────── #

def _pair_mode_b(
    timestamps: List[datetime],
    last_ts: datetime,
) -> Tuple[List[Dict], List[str]]:
    """
    Mode B: F22 all-IN device.
    Ordinal interpretation after deduplication:
      1 punch  → IN only (0-hr incomplete)
      2 punches → Session 1: [0]→[1]
      3 punches → Session 1: [0]→[1], Session 2: [2]→last_ts (inferred)
      4 punches → Session 1: [0]→[1], Session 2: [2]→[3]
    """
    clean, remarks = _dedup_consecutive_mode_b(timestamps)
    n = len(clean)

    if n == 1:
        remarks.append(f"Only one punch ({_fmt_time(clean[0])}); no checkout recorded")
        return [{"in": clean[0], "out": clean[0]}], remarks

    if n == 2:
        return [{"in": clean[0], "out": clean[1]}], remarks

    if n == 3:
        remarks.append(f"Checkout inferred from last punch ({_fmt_time(last_ts)})")
        return [
            {"in": clean[0], "out": clean[1]},
            {"in": clean[2], "out": last_ts},
        ], remarks

    # n >= 4
    return [
        {"in": clean[0], "out": clean[1]},
        {"in": clean[2], "out": clean[3]},
    ], remarks


# ── Helpers ────────────────────────────────────────────────────────────────── #

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


def _has_new_punches(
    db: Session,
    uid: int,
    target_date: date,
    since: datetime,
) -> bool:
    """Return True if any AttendanceLog for uid+date was created after `since`."""
    return db.query(AttendanceLog).filter(
        AttendanceLog.uid == uid,
        func.date(AttendanceLog.timestamp) == target_date,
        AttendanceLog.created_at > since,
    ).first() is not None


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
        Process all punches for uid on target_date.
        If force=False (default), skips records already finalized with no new punches.
        """
        # ── Smart skip: already finalized and no new raw punches ──────────── #
        if not force:
            existing = (
                self.db.query(ProcessedAttendance)
                .filter(
                    ProcessedAttendance.uid  == uid,
                    ProcessedAttendance.date == target_date,
                )
                .first()
            )
            if existing and existing.is_finalized:
                if not _has_new_punches(self.db, uid, target_date, existing.updated_at):
                    return existing   # nothing changed — skip

        # ── Fetch raw logs ────────────────────────────────────────────────── #
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

        # ── Pair punches ──────────────────────────────────────────────────── #
        all_in_mode = all(l.punch_type == 0 for l in logs)
        if all_in_mode:
            sessions, remarks = _pair_mode_b(sorted_ts, last_ts)
        else:
            sessions, remarks = _pair_mode_a(logs, last_ts)

        # ── Calculate hours & status ──────────────────────────────────────── #
        total_hrs = _total_hours(sessions)
        ot_hours  = round(max(0.0, total_hrs - settings.PRESENT_HOURS), 2)
        status    = _determine_status(total_hrs)
        if status == AttendanceStatus.PRESENT and ot_hours > 0:
            status = AttendanceStatus.PRESENT_OT

        if ot_hours > 0:
            remarks.append(f"OT: {ot_hours:.2f}h")

        shift_label = "Break Shift" if len(sessions) == 2 else "Regular"

        # ── Determine finalization ────────────────────────────────────────── #
        # A day is finalized if every session has a real OUT
        # (i.e. no checkout was inferred from the last punch — the
        #  employee explicitly tapped out on the device).
        inferred = any("Checkout inferred" in r or "Only one punch" in r for r in remarks)
        today    = date.today()
        # Also finalize past days even if inferred, since no more punches are coming
        is_finalized = (not inferred) or (target_date < today)

        # ── Serialize sessions ────────────────────────────────────────────── #
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
            is_finalized           = is_finalized,
            is_late                = False,
            is_early_leave         = False,
            late_by_minutes        = 0,
            early_leave_by_minutes = 0,
        )

        # ── Upsert ────────────────────────────────────────────────────────── #
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

    # ── Bulk: only process what actually needs processing ─────────────────── #

    def process_all_pending(self) -> Dict:
        """
        Process only uid+date combinations that either:
          (a) have no ProcessedAttendance record yet, OR
          (b) have a record that is NOT finalized, OR
          (c) have new AttendanceLogs created after the record's updated_at.
        This prevents re-processing every historical record on every sync.
        """
        # All distinct (uid, date) pairs that have raw logs
        all_log_pairs = (
            self.db.query(
                AttendanceLog.uid,
                func.date(AttendanceLog.timestamp).label("log_date"),
            )
            .distinct()
            .all()
        )

        # Build lookup: (uid, date) → ProcessedAttendance for quick access
        processed_lookup: Dict = {}
        all_processed = self.db.query(ProcessedAttendance).all()
        for p in all_processed:
            processed_lookup[(p.uid, p.date)] = p

        ok = skipped = err = 0
        to_process = []

        for uid, log_date in all_log_pairs:
            p = processed_lookup.get((uid, log_date))

            if p is None:
                # Never processed — must process
                to_process.append((uid, log_date))
            elif not p.is_finalized:
                # Not yet finalized (e.g. today's record still open)
                to_process.append((uid, log_date))
            elif _has_new_punches(self.db, uid, log_date, p.updated_at):
                # Finalized but new punches arrived after last processing
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

        total = len(all_log_pairs)
        print(
            f"📊 Attendance processing — "
            f"Total: {total}, Processed: {ok}, Skipped: {skipped}, Errors: {err}"
        )
        return {
            "total":     total,
            "processed": ok,
            "skipped":   skipped,
            "errors":    err,
        }

    def process_date_range(self, uid: int, start: date, end: date):
        results = []
        current = start
        while current <= end:
            rec = self.process_daily_attendance(uid, current)
            if rec:
                results.append(rec)
            current += timedelta(days=1)
        return results

    # ── Summary ────────────────────────────────────────────────────────────── #

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
                "total_overtime_hours":  round(total_ot,    2),
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