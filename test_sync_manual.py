#!/usr/bin/env python3
"""
Test the full sync manually
"""
from app.core.database import SessionLocal
from app.services.device_sync import DeviceSyncService
from datetime import datetime

def test_sync():
    """Manually trigger full sync and check results"""
    db = SessionLocal()
    try:
        print("\n" + "="*80)
        print("🔄 MANUAL SYNC TEST - " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print("="*80 + "\n")
        
        sync_service = DeviceSyncService(db)
        result = sync_service.full_sync()
        
        print("\n" + "="*80)
        print("SYNC RESULT:")
        print("="*80)
        print(f"Status: {result.get('status')}")
        if result.get('error'):
            print(f"Error: {result.get('error')}")
        
        print(f"\nUsers synced:")
        print(f"  {result.get('users', {})}")
        
        print(f"\nLogs synced:")
        print(f"  {result.get('logs', {})}")
        
        print(f"\nAttendance processed:")
        print(f"  {result.get('processed_attendance', {})}")
        
        print(f"\nDevice 1 Info:")
        print(f"  {result.get('device_1_info', {})}")
        
        print(f"\nDevice 2 Info:")
        print(f"  {result.get('device_2_info', {})}")
        
        print("\n" + "="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ Sync failed with error:")
        print(f"{type(e).__name__}: {e}\n")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    test_sync()
