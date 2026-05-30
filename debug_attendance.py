# debug_attendance.py
# Place in project root and run: python debug_attendance.py
# This shows exactly what raw data exists for any employee

import sys
from datetime import date
sys.path.insert(0, '.')

from app.core.database import SessionLocal
from app.models.attendance import AttendanceLog, ProcessedAttendance
from app.models.user import User

db = SessionLocal()

# ── Step 1: Find the employee ─────────────────────────────────────────────── #
name_search = "jayakumari"   # ← change this to search any name
users = db.query(User).filter(User.name.ilike(f"%{name_search}%")).all()

print(f"\n{'='*70}")
print(f"USERS matching '{name_search}':")
print(f"{'='*70}")
for u in users:
    print(f"  DB uid={u.uid}  user_id_str={u.user_id_str}  name={u.name}  active={u.is_active}")

if not users:
    print("  No user found.")
    db.close()
    sys.exit(0)

# Use first match
uid = users[0].uid
print(f"\n→ Using UID={uid} ({users[0].name})")

# ── Step 2: Raw punch logs for April 2026 ────────────────────────────────── #
start = "2026-04-01"
end   = "2026-04-30"

logs = (
    db.query(AttendanceLog)
    .filter(
        AttendanceLog.uid == uid,
        AttendanceLog.timestamp >= f"{start} 00:00:00",
        AttendanceLog.timestamp <= f"{end} 23:59:59",
    )
    .order_by(AttendanceLog.timestamp)
    .all()
)

print(f"\n{'='*70}")
print(f"RAW ATTENDANCE LOGS for UID={uid}, {start} to {end}:")
print(f"Total logs: {len(logs)}")
print(f"{'='*70}")
print(f"{'#':<4} {'Timestamp':<25} {'punch_type':<12} {'status':<8}")
print(f"{'-'*55}")
for i, log in enumerate(logs, 1):
    print(f"{i:<4} {str(log.timestamp):<25} {log.punch_type:<12} {log.status:<8}")

# ── Step 3: Punches per calendar day ─────────────────────────────────────── #
from collections import defaultdict
day_groups = defaultdict(list)
for log in logs:
    day_groups[log.timestamp.date()].append(log)

print(f"\n{'='*70}")
print(f"PUNCHES PER CALENDAR DAY:")
print(f"{'='*70}")
for day in sorted(day_groups.keys()):
    group = day_groups[day]
    times = [l.timestamp.strftime("%H:%M") for l in group]
    types = [str(l.punch_type) for l in group]
    print(f"  {day}  ({len(group)} punches)  times={times}  types={types}")

# ── Step 4: Processed records ─────────────────────────────────────────────── #
processed = (
    db.query(ProcessedAttendance)
    .filter(
        ProcessedAttendance.uid == uid,
        ProcessedAttendance.date >= date(2026, 4, 1),
        ProcessedAttendance.date <= date(2026, 4, 30),
    )
    .order_by(ProcessedAttendance.date)
    .all()
)

print(f"\n{'='*70}")
print(f"PROCESSED ATTENDANCE RECORDS:")
print(f"{'='*70}")
for p in processed:
    fin = "✓FINAL" if p.is_finalized else "OPEN"
    print(
        f"  {p.date}  first_in={p.first_in}  last_out={p.last_out}  "
        f"hrs={p.work_duration_hours}  status={p.status.value}  "
        f"punches={p.total_punches}  [{fin}]"
    )
    if p.remarks:
        print(f"           remarks: {p.remarks}")

# ── Step 5: Check if user_id_str matches uid (key bug check) ─────────────── #
print(f"\n{'='*70}")
print(f"UID vs USER_ID_STR CHECK (important for data integrity):")
print(f"{'='*70}")
all_users = db.query(User).all()
mismatches = [u for u in all_users if u.user_id_str and str(u.uid) != str(u.user_id_str)]
if mismatches:
    print(f"  ⚠️  MISMATCH FOUND — device user_id differs from slot uid:")
    for u in mismatches:
        print(f"     uid={u.uid}  user_id_str={u.user_id_str}  name={u.name}")
    print(f"\n  → This WILL cause attendance logs to be skipped or misattributed.")
    print(f"  → Logs in attendance_logs.uid={u.uid} may actually belong to user_id={u.user_id_str}")
else:
    print(f"  ✅ All users have matching uid and user_id_str")

db.close()
print(f"\n{'='*70}")
print("Debug complete. Share the above output to diagnose issues.")
print(f"{'='*70}\n")