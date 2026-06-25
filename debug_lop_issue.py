#!/usr/bin/env python3
"""
Investigate LOP marking - check specific user logs and processing
"""

from app.core.database import SessionLocal
from app.models.user import User
from app.models.attendance import AttendanceLog, ProcessedAttendance, AttendanceStatus
from datetime import date, datetime
from sqlalchemy import func

def investigate_user_lop():
    """Check why a user has LOP for multiple dates"""
    db = SessionLocal()
    try:
        print("\n" + "="*80)
        print("🔍 LOP INVESTIGATION - UID 35 (Drdurgadevi)")
        print("="*80 + "\n")
        
        uid = 35
        user = db.query(User).filter(User.uid == uid).first()
        
        if not user:
            print(f"❌ User UID {uid} not found\n")
            return
        
        print(f"User: {user.name}")
        print(f"  UID (primary):   {user.uid}")
        print(f"  Device 1 UID:    {user.device_1_uid}")
        print(f"  Device 2 UID:    {user.device_2_uid}\n")
        
        # Check logs from June 16-24
        print("="*80)
        print("RAW ATTENDANCE LOGS - June 16-24")
        print("="*80 + "\n")
        
        start_date = date(2026, 6, 16)
        end_date = date(2026, 6, 24)
        
        logs = db.query(AttendanceLog).filter(
            AttendanceLog.uid == uid,
            func.date(AttendanceLog.timestamp) >= start_date,
            func.date(AttendanceLog.timestamp) <= end_date,
        ).order_by(AttendanceLog.timestamp).all()
        
        print(f"Total logs found: {len(logs)}\n")
        
        if logs:
            print("Logs by date:")
            current_date = None
            for log in logs:
                log_date = log.timestamp.date()
                device_type = "IN (Dev1)" if log.device_ip == "192.168.1.201" else "OUT (Dev2)" if log.device_ip == "192.168.1.4" else "UNKNOWN"
                
                if log_date != current_date:
                    print(f"\n  {log_date}:")
                    current_date = log_date
                
                print(f"    {log.timestamp.strftime('%H:%M:%S')} | {device_type} | {log.device_ip}")
        else:
            print("⚠️  NO LOGS FOUND for this user in this period!\n")
        
        # Check processed records
        print("\n" + "="*80)
        print("PROCESSED ATTENDANCE - June 16-24")
        print("="*80 + "\n")
        
        processed = db.query(ProcessedAttendance).filter(
            ProcessedAttendance.uid == uid,
            ProcessedAttendance.date >= start_date,
            ProcessedAttendance.date <= end_date,
        ).order_by(ProcessedAttendance.date).all()
        
        print(f"Total processed records: {len(processed)}\n")
        
        if processed:
            print("Status by date:")
            for rec in processed:
                status_str = rec.status.value if hasattr(rec.status, 'value') else str(rec.status)
                print(f"  {rec.date} | Status: {status_str:12s} | Hours: {rec.work_duration_hours or 0:5.2f} | Remarks: {rec.remarks or 'None'}")
        
        # Check why they're LOP
        print("\n" + "="*80)
        print("ANALYSIS")
        print("="*80 + "\n")
        
        if len(logs) == 0:
            print("❌ REASON: No attendance logs found for this user in this period")
            print("   Possible causes:")
            print("   1. User UID mismatch between devices")
            print("   2. Employee didn't punch on either device")
            print("   3. Logs weren't synced for some reason")
        else:
            print("✅ Logs found: Data was synced")
            print(f"   Issue: Processor may not be pairing IN/OUT correctly")
            print("   Check: Look at device IP tagging for logs")
            
            # Check device distribution
            dev1_count = sum(1 for log in logs if log.device_ip == "192.168.1.201")
            dev2_count = sum(1 for log in logs if log.device_ip == "192.168.1.4")
            
            print(f"\n   Device distribution:")
            print(f"   - Device 1 (IN):  {dev1_count} logs")
            print(f"   - Device 2 (OUT): {dev2_count} logs")
            
            if dev1_count == 0 or dev2_count == 0:
                print(f"\n   ⚠️  FOUND ISSUE: Missing {('OUT' if dev1_count > 0 else 'IN')} punches!")
                print(f"       Employee only punched on one device")
        
        print("\n" + "="*80 + "\n")
        
    finally:
        db.close()


if __name__ == "__main__":
    investigate_user_lop()
