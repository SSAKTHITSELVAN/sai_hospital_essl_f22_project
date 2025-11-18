from sqlalchemy.orm import Session
from zk import ZK
from datetime import datetime
from typing import Dict, List
from app.models.user import User
from app.models.attendance import AttendanceLog
from app.models.device import Device
from app.config import get_settings
from app.services.attendance_processor import AttendanceProcessor

settings = get_settings()


class DeviceSyncService:
    """
    Service to synchronize data from ESSL F22 device
    Handles connection, data fetching, and error handling
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.device_ip = settings.DEVICE_IP
        self.device_port = settings.DEVICE_PORT
        self.timeout = settings.DEVICE_TIMEOUT
        self.zk = ZK(
            self.device_ip, 
            port=self.device_port, 
            timeout=self.timeout,
            password=0,
            force_udp=False,
            ommit_ping=True
        )
        self.conn = None
    
    def connect(self) -> bool:
        """
        Establish connection to the device
        
        Returns:
            True if connected successfully, False otherwise
        """
        try:
            print(f"🔌 Connecting to device {self.device_ip}:{self.device_port}...")
            self.conn = self.zk.connect()
            self.conn.disable_device()
            print("✅ Device connected and disabled for sync")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            self._log_sync_status("failed", str(e))
            return False
    
    def disconnect(self):
        """Disconnect from device"""
        if self.conn:
            try:
                self.conn.enable_device()
                self.zk.disconnect()
                print("✅ Device disconnected and re-enabled")
            except Exception as e:
                print(f"⚠️ Error during disconnect: {e}")
    
    def sync_users(self) -> Dict:
        """
        Sync users from device to database
        
        Returns:
            Dictionary with sync results
        """
        try:
            users = self.conn.get_users()
            added_count = 0
            updated_count = 0
            
            for device_user in users:
                existing = self.db.query(User).filter(
                    User.uid == device_user.uid
                ).first()
                
                if existing:
                    # Update existing user
                    existing.name = device_user.name
                    existing.privilege = device_user.privilege
                    existing.password = device_user.password
                    existing.group_id = device_user.group_id
                    existing.user_id_str = device_user.user_id
                    existing.card_no = str(device_user.card) if device_user.card else None
                    existing.updated_at = datetime.utcnow()
                    updated_count += 1
                else:
                    # Create new user
                    new_user = User(
                        uid=device_user.uid,
                        name=device_user.name,
                        privilege=device_user.privilege,
                        password=device_user.password,
                        group_id=device_user.group_id,
                        user_id_str=device_user.user_id,
                        card_no=str(device_user.card) if device_user.card else None
                    )
                    self.db.add(new_user)
                    added_count += 1
            
            self.db.commit()
            
            result = {
                "total": len(users),
                "added": added_count,
                "updated": updated_count
            }
            
            print(f"👥 Users synced - Total: {len(users)}, Added: {added_count}, Updated: {updated_count}")
            return result
            
        except Exception as e:
            self.db.rollback()
            print(f"❌ Error syncing users: {e}")
            raise
    
    def sync_attendance_logs(self) -> Dict:
        """
        Sync attendance logs from device to database
        
        Returns:
            Dictionary with sync results
        """
        try:
            logs = self.conn.get_attendance()
            new_count = 0
            duplicate_count = 0
            error_count = 0
            
            for device_log in logs:
                try:
                    # Check if log already exists
                    existing = self.db.query(AttendanceLog).filter(
                        AttendanceLog.uid == device_log.user_id,
                        AttendanceLog.timestamp == device_log.timestamp
                    ).first()
                    
                    if existing:
                        duplicate_count += 1
                        continue
                    
                    # Create new log
                    new_log = AttendanceLog(
                        uid=device_log.user_id,
                        timestamp=device_log.timestamp,
                        punch_type=device_log.punch,
                        status=device_log.status
                    )
                    self.db.add(new_log)
                    new_count += 1
                    
                except Exception as log_error:
                    print(f"⚠️ Error processing log: {log_error}")
                    error_count += 1
                    continue
            
            self.db.commit()
            
            result = {
                "total": len(logs),
                "new": new_count,
                "duplicates": duplicate_count,
                "errors": error_count
            }
            
            print(f"📋 Logs synced - Total: {len(logs)}, New: {new_count}, Duplicates: {duplicate_count}")
            return result
            
        except Exception as e:
            self.db.rollback()
            print(f"❌ Error syncing attendance logs: {e}")
            raise
    
    def get_device_info(self) -> Dict:
        """Get device information"""
        try:
            return {
                "ip": self.device_ip,
                "port": self.device_port,
                "firmware_version": self.conn.get_firmware_version(),
                "serial_number": self.conn.get_serialnumber(),
                "platform": self.conn.get_platform(),
                "device_name": self.conn.get_device_name(),
                "mac_address": self.conn.get_mac()
            }
        except Exception as e:
            print(f"❌ Error getting device info: {e}")
            return {}
    
    def full_sync(self) -> Dict:
        """
        Perform full synchronization: users, logs, and process attendance
        
        Returns:
            Dictionary with complete sync results
        """
        result = {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "users": {},
            "logs": {},
            "processed_attendance": {},
            "device_info": {}
        }
        
        try:
            if not self.connect():
                result["status"] = "failed"
                result["error"] = "Failed to connect to device"
                return result
            
            # Get device info
            result["device_info"] = self.get_device_info()
            
            # Sync users
            result["users"] = self.sync_users()
            
            # Sync attendance logs
            result["logs"] = self.sync_attendance_logs()
            
            # Process attendance
            processor = AttendanceProcessor(self.db)
            result["processed_attendance"] = processor.process_all_pending()
            
            # Log successful sync
            self._log_sync_status("success", "Full sync completed successfully")
            
            print("\n✅ Full synchronization completed successfully!")
            
        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            self._log_sync_status("failed", str(e))
            print(f"\n❌ Sync failed: {e}")
        
        finally:
            self.disconnect()
        
        return result
    
    def _log_sync_status(self, status: str, message: str):
        """Log sync status to device table"""
        try:
            device = self.db.query(Device).filter(
                Device.device_ip == self.device_ip
            ).first()
            
            if not device:
                device = Device(
                    device_ip=self.device_ip,
                    device_port=self.device_port
                )
                self.db.add(device)
            
            device.last_sync_at = datetime.utcnow()
            device.last_sync_status = status
            device.last_sync_message = message
            
            self.db.commit()
        except Exception as e:
            print(f"⚠️ Error logging sync status: {e}")
            self.db.rollback()