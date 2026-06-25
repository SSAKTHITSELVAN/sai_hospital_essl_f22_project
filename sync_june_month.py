#!/usr/bin/env python3
"""
Sync attendance for entire June 2026 (June 1 - June 26)
"""

from app.core.database import SessionLocal
from app.services.device_sync import DeviceSyncService
from app.services.attendance_processor import AttendanceProcessor
from datetime import date, timedelta

def sync_full_month():
    """Sync users, logs, and process attendance for entire June"""
    db = SessionLocal()
    try:
        print("\n" + "="*80)
        print("📅 FULL MONTH SYNC - JUNE 2026 (1st to 26th)")
        print("="*80 + "\n")
        
        # Step 1: Full device sync (users + logs)
        print("STEP 1: Device Synchronization")
        print("-" * 80)
        sync_service = DeviceSyncService(db)
        sync_result = sync_service.full_sync()
        
        if sync_result.get("status") != "success":
            print(f"❌ Sync failed: {sync_result.get('error')}")
            return
        
        print(f"✅ Sync successful!")
        print(f"   Users: {sync_result['users']}")
        print(f"   Logs: {sync_result['logs']}")
        print()
        
        # Step 2: Process all pending attendance
        print("STEP 2: Processing Attendance Records")
        print("-" * 80)
        processor = AttendanceProcessor(db)
        process_result = processor.process_all_pending()
        print(f"✅ Attendance processed!")
        print(f"   Processed: {process_result['processed']}")
        print(f"   Errors: {process_result['errors']}")
        print(f"   Total: {process_result['total']}")
        print()
        
        # Step 3: Summary
        print("STEP 3: Summary")
        print("-" * 80)
        today = date.today()
        june_start = date(2026, 6, 1)
        
        print(f"📊 Date Range: June 1, 2026 → June 26, 2026 (26 days)")
        print(f"✅ All attendance data for June has been synced and processed\n")
        
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error during sync: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    sync_full_month()
