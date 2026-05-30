# diag_2_trace_processor.py
# Run: python diag_2_trace_processor.py
# Traces the EXACT punch pairing logic for any employee — shows WHY each
# day gets the IN/OUT times it does. Use this to verify the fix works.

import sys, json
from datetime import date
sys.path.insert(0, '.')

NAME_SEARCH = "jayakumari"   # ← change to any employee name
MONTH_YEAR  = (2026, 4)      # ← (year, month)

PUNCH_TYPE_NAMES = {
    0: "CHECKIN",
    1: "CHECKOUT",
    2: "BREAK_OUT",
    3: "BREAK_IN",
    4: "OVERTIME_IN",
    5: "OVERTIME_OUT",
}

# Which types count as "IN" direction
IN_TYPES  = frozenset({0, 3, 4})
OUT_TYPES = frozenset({1, 2, 5})

from app.core.database import SessionLocal
from app.models.attendance import AttendanceLog, ProcessedAttendance
from app.models.user import User
from app.config import get_settings

settings = get_settings()
db = SessionLocal()

# ── Find user ─────────────────────────────────────────────────────────────── #
users = db.query(User).filter(User.name.ilike(f"%{NAME_SEARCH}%")).all()
print(f"\n{'='*70}")
print(f"PROCESSOR TRACE — '{NAME_SEARCH}' — {MONTH_YEAR[1]}/{MONTH_YEAR[0]}")
print(f"DAY_START_TIME = {settings.DAY_START_TIME}")
print(f"{'='*70}")

if not users:
    print("No user found."); db.close(); sys.exit(0)

user = users[0]
print(f"User: {user.name}  uid={user.uid}  user_id_str={user.user_id_str}")

# ── Fetch all raw logs for this month via logical day windows ─────────────── #
import calendar as cal
from datetime import datetime, timedelta, time

day_start = settings.day_start
year, month = MONTH_YEAR
_, days_in_month = cal.monthrange(year, month)

for day_num in range(1, days_in_month + 1):
    logical_date = date(year, month, day_num)
    win_start    = datetime.combine(logical_date, day_start)
    win_end      = datetime.combine(logical_date + timedelta(days=1), day_start)

    logs = (
        db.query(AttendanceLog)
        .filter(
            AttendanceLog.uid       == user.uid,
            AttendanceLog.timestamp >= win_start,
            AttendanceLog.timestamp <  win_end,
        )
        .order_by(AttendanceLog.timestamp)
        .all()
    )

    if not logs:
        continue

    print(f"\n{'─'*70}")
    print(f"  {logical_date}  ({len(logs)} punches in window {win_start.strftime('%H:%M')}→{win_end.strftime('%H:%M')})")
    print(f"  Raw punches:")
    for l in logs:
        pt_name = PUNCH_TYPE_NAMES.get(l.punch_type, f"?({l.punch_type})")
        is_in   = l.punch_type in IN_TYPES
        direction = "→IN " if is_in else "←OUT"
        print(f"    {l.timestamp.strftime('%Y-%m-%d %H:%M:%S')}  type={l.punch_type} ({pt_name})  {direction}")

    # Check if all type 0 (Mode B) or mixed (Mode A)
    all_type_zero = all(l.punch_type == 0 for l in logs)
    mode = "Mode B (all type-0, gap-based)" if all_type_zero else "Mode A (real punch types)"
    print(f"\n  Mode detected: {mode}")

    # ── Trace Mode A grouping (new logic) ────────────────────────────────── #
    if not all_type_zero:
        print(f"\n  Grouping consecutive same-direction punches:")
        print(f"  (IN types: 0=CHECKIN, 3=BREAK_IN, 4=OT_IN | OUT types: 1=CHECKOUT, 2=BREAK_OUT, 5=OT_OUT)")

        groups = []
        i = 0
        while i < len(logs):
            curr_is_in = logs[i].punch_type in IN_TYPES
            group = [logs[i]]
            j = i + 1
            while j < len(logs) and (logs[j].punch_type in IN_TYPES) == curr_is_in:
                group.append(logs[j])
                j += 1

            direction = "IN" if curr_is_in else "OUT"
            if curr_is_in:
                canonical = group[0]   # FIRST IN = real arrival time
                dropped   = group[1:]
            else:
                canonical = group[-1]  # LAST OUT = real departure time
                dropped   = group[:-1]

            print(f"    [{direction} group]: ", end="")
            print(", ".join(l.timestamp.strftime("%H:%M") for l in group), end="")
            print(f"  → keep {canonical.timestamp.strftime('%H:%M')}", end="")
            if dropped:
                print(f"  [drop: {', '.join(l.timestamp.strftime('%H:%M') for l in dropped)}]", end="")
            print()
            groups.append((curr_is_in, canonical))
            i = j

        print(f"\n  Pairing IN→OUT sessions:")
        j = 0
        sessions = []
        while j < len(groups):
            curr_is_in, curr_log = groups[j]
            if not curr_is_in:
                print(f"    ⚠ Orphan OUT at {curr_log.timestamp.strftime('%H:%M')} — no matching IN (end of prev shift)")
                j += 1; continue
            in_ts = curr_log.timestamp
            if j + 1 < len(groups) and not groups[j+1][0]:
                out_ts = groups[j+1][1].timestamp
                hours  = (out_ts - in_ts).total_seconds() / 3600
                print(f"    Session {len(sessions)+1}: IN={in_ts.strftime('%H:%M')} → OUT={out_ts.strftime('%H:%M')} = {hours:.2f}h")
                sessions.append({"in": in_ts, "out": out_ts, "hours": hours})
                j += 2
            else:
                print(f"    Session {len(sessions)+1}: IN={in_ts.strftime('%H:%M')} → OUT=??? (awaiting checkout)")
                sessions.append({"in": in_ts, "out": None, "hours": 0})
                j += 1

        total = sum(s["hours"] for s in sessions)
        print(f"    TOTAL: {total:.2f}h")

    else:
        # Mode B trace
        min_gap = getattr(settings, "MIN_BREAK_GAP_MINUTES", 30)
        timestamps = [l.timestamp for l in logs]
        print(f"\n  Gap-based grouping (min_gap={min_gap} min):")
        groups_b = [[timestamps[0]]]
        for k in range(1, len(timestamps)):
            gap = (timestamps[k] - timestamps[k-1]).total_seconds() / 60
            if gap <= min_gap:
                groups_b[-1].append(timestamps[k])
            else:
                groups_b.append([timestamps[k]])

        canonical = []
        for gi, grp in enumerate(groups_b):
            direction = "IN" if gi % 2 == 0 else "OUT"
            print(f"    [{direction} group]: {', '.join(t.strftime('%H:%M') for t in grp)} → keep {grp[-1].strftime('%H:%M')}")
            canonical.append(grp[-1])

        print(f"\n  Paired sessions:")
        total = 0.0
        for k in range(0, len(canonical), 2):
            in_ts = canonical[k]
            out_ts = canonical[k+1] if k+1 < len(canonical) else None
            if out_ts:
                h = (out_ts - in_ts).total_seconds() / 3600
                total += h
                print(f"    Session {k//2+1}: {in_ts.strftime('%H:%M')} → {out_ts.strftime('%H:%M')} = {h:.2f}h")
            else:
                print(f"    Session {k//2+1}: {in_ts.strftime('%H:%M')} → ??? (open)")
        print(f"    TOTAL: {total:.2f}h")

    # ── Compare to what's stored in DB ────────────────────────────────────── #
    stored = (
        db.query(ProcessedAttendance)
        .filter(ProcessedAttendance.uid == user.uid, ProcessedAttendance.date == logical_date)
        .first()
    )
    if stored:
        print(f"\n  DB stored: first_in={stored.first_in}  last_out={stored.last_out}")
        print(f"            hours={stored.work_duration_hours}  status={stored.status.value}")
        print(f"            remarks={stored.remarks}")
    else:
        print(f"\n  DB stored: (no processed record)")

db.close()
print(f"\n{'='*70}")
print("Share this output to verify the fix is working correctly.")
print(f"{'='*70}\n")