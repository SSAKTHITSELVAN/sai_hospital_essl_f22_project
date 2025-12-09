# app/background/tasks.py
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, date, timedelta
from app.core.database import SessionLocal
from app.services.device_sync import DeviceSyncService
from app.services.lop_service import LOPService
from app.config import get_settings

settings = get_settings()


class BackgroundSyncManager:
    """
    Manages background synchronization tasks
    Automatically syncs data from device at regular intervals
    """
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.sync_interval_minutes = settings.SYNC_INTERVAL_MINUTES
    
    def sync_device_data(self):
        """Background task to sync device data"""
        db = SessionLocal()
        try:
            print(f"\n{'='*80}")
            print(f"🔄 Background Sync Started - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*80}")
            
            sync_service = DeviceSyncService(db)
            result = sync_service.full_sync()
            
            if result["status"] == "success":
                print(f"✅ Background sync completed successfully")
                print(f"   Users: {result['users']}")
                print(f"   Logs: {result['logs']}")
                print(f"   Processed: {result['processed_attendance']}")
            else:
                print(f"❌ Background sync failed: {result.get('error', 'Unknown error')}")
            
            print(f"{'='*80}\n")
            
        except Exception as e:
            print(f"❌ Background sync error: {e}")
        finally:
            db.close()
    
    def check_and_mark_lop(self):
        """
        Daily task to check absentees and mark LOP
        Runs at 7 AM every day to check previous day's attendance
        """
        db = SessionLocal()
        try:
            print(f"\n{'='*80}")
            print(f"📋 LOP Check Started - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*80}")
            
            # Check yesterday's attendance
            yesterday = date.today() - timedelta(days=1)
            print(f"🔍 Checking attendance for: {yesterday.isoformat()}")
            
            lop_service = LOPService(db)
            
            # First, get absentees
            absentee_data = lop_service.get_absentees_for_date(yesterday)
            print(f"👥 Total Employees: {absentee_data['total_employees']}")
            print(f"✅ Present: {absentee_data['present_employees']}")
            print(f"❌ Absent: {absentee_data['absent_employees']}")
            
            if absentee_data['absent_employees'] > 0:
                print(f"\n📝 Marking LOP for {absentee_data['absent_employees']} absentees...")
                
                # Mark LOP for all absentees
                result = lop_service.mark_lop_for_date(yesterday)
                
                if result["status"] == "success":
                    print(f"✅ LOP marked successfully")
                    print(f"   Marked: {result['marked']}")
                    print(f"   Skipped: {result['skipped']}")
                    if result['errors']:
                        print(f"   Errors: {len(result['errors'])}")
                        for error in result['errors']:
                            print(f"      - UID {error['uid']}: {error['error']}")
                else:
                    print(f"❌ LOP marking failed: {result.get('message', 'Unknown error')}")
            else:
                print(f"✅ No absentees found - All employees present!")
            
            print(f"{'='*80}\n")
            
        except Exception as e:
            print(f"❌ LOP check error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            db.close()
    
    def start(self):
        """Start the background scheduler"""
        # Add device sync job (every N minutes)
        self.scheduler.add_job(
            func=self.sync_device_data,
            trigger=IntervalTrigger(minutes=self.sync_interval_minutes),
            id='device_sync_job',
            name='Device Synchronization',
            replace_existing=True
        )
        
        # Add LOP check job (daily at 7:00 AM)
        self.scheduler.add_job(
            func=self.check_and_mark_lop,
            trigger=CronTrigger(hour=7, minute=0),  # Run at 7:00 AM every day
            id='lop_check_job',
            name='Daily LOP Check',
            replace_existing=True
        )
        
        # Start scheduler
        self.scheduler.start()
        print(f"🚀 Background scheduler started")
        print(f"⏰ Sync interval: Every {self.sync_interval_minutes} minutes")
        print(f"⏰ LOP check: Daily at 7:00 AM")
        
        # Run initial sync
        print("🔄 Running initial synchronization...")
        self.sync_device_data()
    
    def stop(self):
        """Stop the background scheduler"""
        self.scheduler.shutdown()
        print("🛑 Background scheduler stopped")


# Global scheduler instance
sync_manager = BackgroundSyncManager()