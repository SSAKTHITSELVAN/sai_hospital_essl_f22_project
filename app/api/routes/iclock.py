
# app/api/routes/iclock.py
from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.database import get_db
from app.models.attendance import AttendanceLog
from app.services.attendance_processor import AttendanceProcessor

router = APIRouter(prefix="/iclock", tags=["iClock Protocol"])


@router.post("/cdata")
@router.get("/cdata")
async def iclock_cdata(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Endpoint for F22 device to push attendance data
    Device sends data to: http://YOUR_IP:8000/iclock/cdata
    """
    try:
        # Parse device data
        if request.method == "POST":
            body = await request.body()
            data_str = body.decode('utf-8')
        else:
            data_str = str(request.query_params)
        
        print(f"📥 Received data from device: {data_str}")
        
        # Parse attendance records
        # Format: ATTLOG PIN=X&Time=YYYY-MM-DD HH:MM:SS&Status=0&Verify=1
        if "ATTLOG" in data_str:
            records = parse_attlog(data_str)
            
            for record in records:
                # Save to database
                log = AttendanceLog(
                    uid=record["pin"],
                    timestamp=record["timestamp"],
                    punch_type=record.get("status", 0),
                    status=record.get("verify", 0),
                    device_id=record.get("sn")
                )
                db.add(log)
            
            db.commit()
            
            # Process attendance immediately
            processor = AttendanceProcessor(db)
            for record in records:
                processor.process_daily_attendance(
                    record["pin"],
                    record["timestamp"].date()
                )
            
            return "OK"
        
        return "OK"
        
    except Exception as e:
        print(f"❌ Error processing device data: {e}")
        return "OK"  # Always return OK to device


def parse_attlog(data: str) -> list:
    """Parse ATTLOG format from device"""
    records = []
    lines = data.split('\n')
    
    for line in lines:
        if "PIN=" in line:
            record = {}
            parts = line.split('&')
            
            for part in parts:
                if '=' in part:
                    key, value = part.split('=', 1)
                    key = key.strip().lower()
                    
                    if key == "pin":
                        record["pin"] = int(value)
                    elif key == "time":
                        record["timestamp"] = datetime.strptime(
                            value, "%Y-%m-%d %H:%M:%S"
                        )
                    elif key == "status":
                        record["status"] = int(value)
                    elif key == "verify":
                        record["verify"] = int(value)
                    elif key == "sn":
                        record["sn"] = value
            
            if "pin" in record and "timestamp" in record:
                records.append(record)
    
    return records