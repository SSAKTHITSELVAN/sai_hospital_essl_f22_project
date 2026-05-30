# app/api/routes/iclock.py
"""
Real-time punch webhook for the ESSL F22 device.

Key fix: device_log PIN is the enrollment user_id, not the DB slot uid.
We now resolve PIN → User.uid via user_id_str before inserting AttendanceLog,
preventing FK violations and wrong user associations.
"""
from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.database import get_db
from app.models.attendance import AttendanceLog
from app.models.user import User
from app.services.attendance_processor import AttendanceProcessor

router = APIRouter(prefix="/iclock", tags=["iClock Protocol"])


def _resolve_uid(db: Session, pin: str) -> int | None:
    """
    Resolve a device PIN (enrollment user_id) to the DB users.uid (slot number).

    Tries user_id_str match first (correct), then falls back to numeric uid
    match for devices where user_id == uid.

    Returns None if no matching user is found.
    """
    # Primary: match on user_id_str (enrollment ID stored during sync)
    user = db.query(User).filter(
        User.user_id_str == str(pin),
        User.is_active   == True,
    ).first()

    if user:
        return user.uid

    # Fallback: try treating PIN as a direct uid (works when user_id == uid)
    try:
        uid_int = int(pin)
        user = db.query(User).filter(
            User.uid       == uid_int,
            User.is_active == True,
        ).first()
        return user.uid if user else None
    except (ValueError, TypeError):
        return None


@router.post("/cdata")
@router.get("/cdata")
async def iclock_cdata(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Endpoint for the F22 device to push attendance data in real-time.
    Device is configured to POST to: http://YOUR_IP:8000/iclock/cdata
    Always returns "OK" (device expects this exact string).
    """
    try:
        if request.method == "POST":
            body     = await request.body()
            data_str = body.decode("utf-8")
        else:
            data_str = str(request.query_params)

        print(f"📥 Received from device: {data_str[:200]}")

        if "ATTLOG" not in data_str:
            return "OK"

        records = _parse_attlog(data_str)

        for record in records:
            pin = str(record["pin"])

            # Resolve PIN → actual DB uid
            matched_uid = _resolve_uid(db, pin)
            if matched_uid is None:
                print(f"⚠️  Skipping push log — PIN '{pin}' not found in users table")
                continue

            # Skip exact duplicates
            existing = db.query(AttendanceLog).filter(
                AttendanceLog.uid       == matched_uid,
                AttendanceLog.timestamp == record["timestamp"],
            ).first()
            if existing:
                continue

            log = AttendanceLog(
                uid        = matched_uid,
                timestamp  = record["timestamp"],
                punch_type = record.get("status", 0),
                status     = record.get("verify", 0),
                device_id  = record.get("sn"),
            )
            db.add(log)

        db.commit()

        # Process attendance for each affected user+date
        processor = AttendanceProcessor(db)
        seen = set()
        for record in records:
            pin = str(record["pin"])
            matched_uid = _resolve_uid(db, pin)
            if matched_uid is None:
                continue
            key = (matched_uid, record["timestamp"].date())
            if key not in seen:
                seen.add(key)
                processor.process_daily_attendance(matched_uid, record["timestamp"].date())

        return "OK"

    except Exception as e:
        print(f"❌ Error processing device push: {e}")
        return "OK"   # Always return OK so device doesn't retry endlessly


def _parse_attlog(data: str) -> list:
    """Parse ATTLOG push format from ESSL device."""
    records = []
    for line in data.split("\n"):
        if "PIN=" not in line:
            continue
        record = {}
        for part in line.split("&"):
            if "=" not in part:
                continue
            key, _, value = part.partition("=")
            key = key.strip().lower()
            if key == "pin":
                record["pin"] = value.strip()
            elif key == "time":
                try:
                    record["timestamp"] = datetime.strptime(
                        value.strip(), "%Y-%m-%d %H:%M:%S"
                    )
                except ValueError:
                    pass
            elif key == "status":
                try:
                    record["status"] = int(value)
                except ValueError:
                    record["status"] = 0
            elif key == "verify":
                try:
                    record["verify"] = int(value)
                except ValueError:
                    record["verify"] = 0
            elif key == "sn":
                record["sn"] = value.strip()

        if "pin" in record and "timestamp" in record:
            records.append(record)

    return records