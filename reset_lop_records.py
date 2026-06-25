#!/usr/bin/env python3
"""
Fix finalized LOP records by resetting them for re-processing
"""

from app.core.database import SessionLocal
from app.models.attendance import ProcessedAttendance, AttendanceStatus
from datetime import date
from sqlalchemy import func

def reset_lop_records():
    """Reset finalized LOP records so processor can re-process them"""
    db = SessionLocal()
    try:
        print("\n" + "="*80)
        print("🔧 RESETTING FINALIZED LOP RECORDS")
        print("="*80 + "\n")
        
        # Find all LOP records that are finalized
        lop_records = db.query(ProcessedAttendance).filter(
            ProcessedAttendance.status == AttendanceStatus.LOP,
            ProcessedAttendance.is_finalized == True,
        ).all()
        
        print(f"Found {len(lop_records)} finalized LOP records\n")
        
        if not lop_records:
            print("✅ No finalized LOP records to reset\n")
            return
        
        # Delete these LOP records so processor can recreate them with actual data
        deleted_count = 0
        for record in lop_records:
            user_name = record.user.name if record.user else "Unknown"
            print(f"  Deleting: {user_name:20s} | {record.date} | Status: {record.status.value}")
            db.delete(record)
            deleted_count += 1
        
        db.commit()
        
        print(f"\n✅ Deleted {deleted_count} finalized LOP records")
        print("   Processor will now re-create these with actual attendance data\n")
        
        print("="*80)
        print("NEXT STEP: Run sync again to re-process these dates")
        print("  saienv\\Scripts\\python sync_june_month.py")
        print("="*80 + "\n")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}\n")
    finally:
        db.close()


if __name__ == "__main__":
    reset_lop_records()
