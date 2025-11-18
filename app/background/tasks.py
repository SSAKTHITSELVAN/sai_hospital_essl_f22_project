from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from app.core.database import SessionLocal
from app.services.device_sync import DeviceSyncService
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
    
    def start(self):
        """Start the background scheduler"""
        # Add sync job
        self.scheduler.add_job(
            func=self.sync_device_data,
            trigger=IntervalTrigger(minutes=self.sync_interval_minutes),
            id='device_sync_job',
            name='Device Synchronization',
            replace_existing=True
        )
        
        # Start scheduler
        self.scheduler.start()
        print(f"🚀 Background scheduler started")
        print(f"⏰ Sync interval: Every {self.sync_interval_minutes} minutes")
        
        # Run initial sync
        print("🔄 Running initial synchronization...")
        self.sync_device_data()
    
    def stop(self):
        """Stop the background scheduler"""
        self.scheduler.shutdown()
        print("🛑 Background scheduler stopped")


# Global scheduler instance
sync_manager = BackgroundSyncManager()