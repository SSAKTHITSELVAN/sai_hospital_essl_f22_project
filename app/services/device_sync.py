# app/services/device_sync.py
"""
Dual ESSL F22 Device Sync Service
──────────────────────────────────────────────────────────────────────────────

ARCHITECTURE:
  • Device 1 (192.168.1.201) = IN device  → all punches treated as CHECK-IN
  • Device 2 (192.168.1.35)  = OUT device → all punches treated as CHECK-OUT
  • User matching: BY NAME (case-insensitive, normalized)
    - UIDs may differ across devices, but names are unique
  • device_ip stored in AttendanceLog to identify source

KEY FEATURES:
  1. Name-based user synchronization across both devices
  2. Unified user registry (one user record per unique name)
  3. Device IP tracking for IN/OUT determination
  4. Thread-safe ZK connection management (_ZK_LOCK)
  5. Duplicate prevention

FLOW:
  1. Sync users from both devices → merge by name
  2. Sync attendance logs from both devices → tag with device_ip
  3. Processor reads device_ip to determine IN vs OUT
"""

import threading
from sqlalchemy.orm import Session
from zk import ZK
from datetime import datetime
from typing import Dict, List, Tuple

from app.models.user import User
from app.models.attendance import AttendanceLog
from app.models.device import Device
from app.config import get_settings
from app.services.attendance_processor import AttendanceProcessor

settings = get_settings()

# Module-level lock — ensures only ONE ZK connection exists at any point in time
_ZK_LOCK = threading.Lock()


def _normalize_name(name: str) -> str:
    """Normalize name for matching: strip whitespace, lowercase."""
    return name.strip().lower()


class DeviceSyncService:
    """
    Dual-device synchronization service.

    Syncs users and attendance from two ESSL F22 devices:
    - Device 1: IN device (all punches = CHECK-IN)
    - Device 2: OUT device (all punches = CHECK-OUT)

    Thread-safe: uses _ZK_LOCK to prevent concurrent connections.
    """

    def __init__(self, db: Session):
        self.db = db

        # Device 1 (IN device)
        self.device_1_ip      = settings.DEVICE_1_IP
        self.device_1_port    = settings.DEVICE_1_PORT
        self.device_1_timeout = settings.DEVICE_1_TIMEOUT
        self.zk_1 = ZK(
            self.device_1_ip,
            port=self.device_1_port,
            timeout=self.device_1_timeout,
            password=0,
            force_udp=False,
            ommit_ping=True,
        )

        # Device 2 (OUT device)
        self.device_2_ip      = settings.DEVICE_2_IP
        self.device_2_port    = settings.DEVICE_2_PORT
        self.device_2_timeout = settings.DEVICE_2_TIMEOUT
        self.zk_2 = ZK(
            self.device_2_ip,
            port=self.device_2_port,
            timeout=self.device_2_timeout,
            password=0,
            force_udp=False,
            ommit_ping=True,
        )

        self.conn_1 = None
        self.conn_2 = None

    def connect_device(self, device_num: int, disable: bool = True) -> bool:
        """
        Connect to specified device.

        Args:
            device_num: 1 or 2
            disable: If True, disable the device during operation
        """
        try:
            if device_num == 1:
                print(f"🔌 Connecting to Device 1 (IN) {self.device_1_ip}:{self.device_1_port}...")
                self.conn_1 = self.zk_1.connect()
                if disable:
                    self.conn_1.disable_device()
                    print("✅ Device 1 connected and disabled for sync")
                else:
                    print("✅ Device 1 connected (read-only, not disabled)")
            else:
                print(f"🔌 Connecting to Device 2 (OUT) {self.device_2_ip}:{self.device_2_port}...")
                self.conn_2 = self.zk_2.connect()
                if disable:
                    self.conn_2.disable_device()
                    print("✅ Device 2 connected and disabled for sync")
                else:
                    print("✅ Device 2 connected (read-only, not disabled)")
            return True
        except Exception as e:
            print(f"❌ Device {device_num} connection failed: {e}")
            return False

    def disconnect_device(self, device_num: int):
        """Disconnect specified device."""
        try:
            if device_num == 1 and self.conn_1:
                self.conn_1.enable_device()
                self.zk_1.disconnect()
                self.conn_1 = None
                print("✅ Device 1 disconnected and re-enabled")
            elif device_num == 2 and self.conn_2:
                self.conn_2.enable_device()
                self.zk_2.disconnect()
                self.conn_2 = None
                print("✅ Device 2 disconnected and re-enabled")
        except Exception as e:
            print(f"⚠️ Error disconnecting Device {device_num}: {e}")

    def sync_users(self) -> Dict:
        """
        Sync users from BOTH devices and merge by name.

        NEW LOGIC:
        - Each user has device_1_uid and device_2_uid columns
        - Users are matched by NAME (case-insensitive)
        - If user exists on Device 1 → store in device_1_uid
        - If user exists on Device 2 → store in device_2_uid
        - If user exists on both → store both UIDs
        - Primary uid = device_1_uid if available, else device_2_uid

        Returns:
            Dict with sync statistics
        """
        try:
            # Fetch users from both devices
            device_1_users = self.conn_1.get_users() if self.conn_1 else []
            device_2_users = self.conn_2.get_users() if self.conn_2 else []

            print(f"📥 Fetched {len(device_1_users)} users from Device 1 (IN)")
            print(f"📥 Fetched {len(device_2_users)} users from Device 2 (OUT)")

            # Build name → device UIDs mapping
            # Key: normalized name, Value: {device_1_uid, device_2_uid, user_obj}
            users_by_name: Dict[str, Dict] = {}

            # Collect Device 1 users
            for device_user in device_1_users:
                norm_name = _normalize_name(device_user.name)
                if norm_name not in users_by_name:
                    users_by_name[norm_name] = {
                        'device_1_uid': None,
                        'device_2_uid': None,
                        'device_1_user': None,
                        'device_2_user': None,
                    }
                users_by_name[norm_name]['device_1_uid'] = device_user.uid
                users_by_name[norm_name]['device_1_user'] = device_user

            # Collect Device 2 users
            for device_user in device_2_users:
                norm_name = _normalize_name(device_user.name)
                if norm_name not in users_by_name:
                    users_by_name[norm_name] = {
                        'device_1_uid': None,
                        'device_2_uid': None,
                        'device_1_user': None,
                        'device_2_user': None,
                    }
                users_by_name[norm_name]['device_2_uid'] = device_user.uid
                users_by_name[norm_name]['device_2_user'] = device_user

            added_count   = 0
            updated_count = 0
            skipped_count = 0

            # Process each unique name
            for norm_name, user_data in users_by_name.items():
                # Get primary user object (prefer Device 1)
                primary_user = user_data['device_1_user'] or user_data['device_2_user']

                # Determine primary UID (prefer Device 1)
                primary_uid = user_data['device_1_uid'] or user_data['device_2_uid']

                # Check if user exists in DB by name
                existing = self.db.query(User).filter(
                    User.name.ilike(primary_user.name)
                ).first()

                if existing:
                    # Update existing user with both device UIDs
                    if user_data['device_1_uid']:
                        existing.device_1_uid = user_data['device_1_uid']
                    if user_data['device_2_uid']:
                        existing.device_2_uid = user_data['device_2_uid']

                    # Update primary UID if needed
                    existing.uid = user_data['device_1_uid'] or user_data['device_2_uid']

                    # Update other fields from primary user
                    existing.privilege   = primary_user.privilege
                    existing.password    = primary_user.password
                    existing.group_id    = primary_user.group_id
                    existing.is_active   = True
                    existing.updated_at  = datetime.utcnow()
                    updated_count += 1

                    dev_info = []
                    if user_data['device_1_uid']:
                        dev_info.append(f"Dev1:UID={user_data['device_1_uid']}")
                    if user_data['device_2_uid']:
                        dev_info.append(f"Dev2:UID={user_data['device_2_uid']}")
                    print(f"✅ Updated user: {primary_user.name} ({', '.join(dev_info)})")
                else:
                    # Check if UID already exists (conflict resolution)
                    uid_conflict = self.db.query(User).filter(User.uid == primary_uid).first()
                    
                    if uid_conflict:
                        # UID conflict: keep existing user, just update device UIDs
                        print(f"⚠️  UID conflict for {primary_user.name}: UID {primary_uid} exists as {uid_conflict.name}")
                        if user_data['device_1_uid'] and user_data['device_1_uid'] != uid_conflict.device_1_uid:
                            uid_conflict.device_1_uid = user_data['device_1_uid']
                        if user_data['device_2_uid'] and user_data['device_2_uid'] != uid_conflict.device_2_uid:
                            uid_conflict.device_2_uid = user_data['device_2_uid']
                        uid_conflict.updated_at = datetime.utcnow()
                        updated_count += 1
                        skipped_count += 1
                    else:
                        # Create new user with both device UIDs
                        new_user = User(
                            uid           = primary_uid,
                            device_1_uid  = user_data['device_1_uid'],
                            device_2_uid  = user_data['device_2_uid'],
                            name          = primary_user.name,
                            privilege     = primary_user.privilege,
                            password      = primary_user.password,
                            group_id      = primary_user.group_id,
                            user_id_str   = str(primary_user.user_id),
                            card_no       = str(primary_user.card) if primary_user.card else None,
                            is_active     = True,
                        )
                        self.db.add(new_user)
                        added_count += 1

                        dev_info = []
                        if user_data['device_1_uid']:
                            dev_info.append(f"Dev1:UID={user_data['device_1_uid']}")
                        if user_data['device_2_uid']:
                            dev_info.append(f"Dev2:UID={user_data['device_2_uid']}")
                        print(f"➕ Added new user: {primary_user.name} ({', '.join(dev_info)})")

            self.db.commit()

            result = {
                "total_unique_names": len(users_by_name),
                "device_1_users":     len(device_1_users),
                "device_2_users":     len(device_2_users),
                "added":              added_count,
                "updated":            updated_count,
                "skipped":            skipped_count,
            }
            print(
                f"\n👥 Users synced — Unique names: {len(users_by_name)}, "
                f"Device1: {len(device_1_users)}, Device2: {len(device_2_users)}, "
                f"Added: {added_count}, Updated: {updated_count}, Skipped: {skipped_count}"
            )
            return result

        except Exception as e:
            self.db.rollback()
            print(f"❌ Error syncing users: {e}")
            raise

    def sync_attendance_logs(self) -> Dict:
        """
        Sync attendance logs from BOTH devices.

        Logic:
        - Fetch attendance from Device 1 → tag with device_1_ip (IN punches)
        - Fetch attendance from Device 2 → tag with device_2_ip (OUT punches)
        - Match users by NAME (not UID)
        - Store device_ip for processor to determine IN/OUT

        Returns:
            Dict with sync statistics
        """
        try:
            # Fetch attendance from both devices
            logs_dev1 = self.conn_1.get_attendance() if self.conn_1 else []
            logs_dev2 = self.conn_2.get_attendance() if self.conn_2 else []

            print(f"📥 Fetched {len(logs_dev1)} logs from Device 1 (IN)")
            print(f"📥 Fetched {len(logs_dev2)} logs from Device 2 (OUT)")

            new_count       = 0
            duplicate_count = 0
            skipped_count   = 0
            error_count     = 0

            # Build device UID → DB user mappings
            device_1_uid_to_user: Dict[int, User] = {}
            device_2_uid_to_user: Dict[int, User] = {}

            for user in self.db.query(User).filter(User.is_active == True).all():
                if user.device_1_uid:
                    device_1_uid_to_user[user.device_1_uid] = user
                if user.device_2_uid:
                    device_2_uid_to_user[user.device_2_uid] = user

            # Fetch device users for UID mapping
            device_1_users_list = self.conn_1.get_users() if self.conn_1 else []
            device_2_users_list = self.conn_2.get_users() if self.conn_2 else []

            # Process Device 1 logs (IN device)
            for device_log in logs_dev1:
                try:
                    # Find device user by user_id
                    device_user = next((u for u in device_1_users_list if u.user_id == device_log.user_id), None)

                    if not device_user:
                        print(f"⚠️  Device 1: Unknown user_id {device_log.user_id}")
                        skipped_count += 1
                        continue

                    # Match by Device 1 UID
                    db_user = device_1_uid_to_user.get(device_user.uid)
                    if not db_user:
                        print(f"⚠️  Device 1: UID {device_user.uid} ({device_user.name}) not in DB")
                        skipped_count += 1
                        continue

                    # Check for duplicate
                    existing = self.db.query(AttendanceLog).filter(
                        AttendanceLog.uid       == db_user.uid,
                        AttendanceLog.timestamp == device_log.timestamp,
                        AttendanceLog.device_ip == self.device_1_ip,
                    ).first()

                    if existing:
                        duplicate_count += 1
                        continue

                    # Create new log with Device 1 IP
                    new_log = AttendanceLog(
                        uid        = db_user.uid,
                        timestamp  = device_log.timestamp,
                        punch_type = device_log.punch,
                        status     = device_log.status,
                        device_ip  = self.device_1_ip,  # Tag as IN device
                    )
                    self.db.add(new_log)
                    new_count += 1

                except Exception as log_error:
                    print(f"⚠️ Device 1 log error: {log_error}")
                    error_count += 1
                    continue

            # Process Device 2 logs (OUT device)
            for device_log in logs_dev2:
                try:
                    # Find device user by user_id
                    device_user = next((u for u in device_2_users_list if u.user_id == device_log.user_id), None)

                    if not device_user:
                        print(f"⚠️  Device 2: Unknown user_id {device_log.user_id}")
                        skipped_count += 1
                        continue

                    # Match by Device 2 UID
                    db_user = device_2_uid_to_user.get(device_user.uid)
                    if not db_user:
                        print(f"⚠️  Device 2: UID {device_user.uid} ({device_user.name}) not in DB")
                        skipped_count += 1
                        continue

                    # Check for duplicate
                    existing = self.db.query(AttendanceLog).filter(
                        AttendanceLog.uid       == db_user.uid,
                        AttendanceLog.timestamp == device_log.timestamp,
                        AttendanceLog.device_ip == self.device_2_ip,
                    ).first()

                    if existing:
                        duplicate_count += 1
                        continue

                    # Create new log with Device 2 IP
                    new_log = AttendanceLog(
                        uid        = db_user.uid,
                        timestamp  = device_log.timestamp,
                        punch_type = device_log.punch,
                        status     = device_log.status,
                        device_ip  = self.device_2_ip,  # Tag as OUT device
                    )
                    self.db.add(new_log)
                    new_count += 1

                except Exception as log_error:
                    print(f"⚠️ Device 2 log error: {log_error}")
                    error_count += 1
                    continue

            self.db.commit()

            result = {
                "total":              len(logs_dev1) + len(logs_dev2),
                "device_1_logs":      len(logs_dev1),
                "device_2_logs":      len(logs_dev2),
                "new":                new_count,
                "duplicates":         duplicate_count,
                "skipped_unknown":    skipped_count,
                "errors":             error_count,
            }
            print(
                f"📋 Logs synced — Total: {len(logs_dev1) + len(logs_dev2)}, "
                f"New: {new_count}, Duplicates: {duplicate_count}, Skipped: {skipped_count}"
            )
            return result

        except Exception as e:
            self.db.rollback()
            print(f"❌ Error syncing attendance logs: {e}")
            raise

    def get_device_info(self, device_num: int) -> Dict:
        """Get device info for specified device."""
        try:
            conn = self.conn_1 if device_num == 1 else self.conn_2
            device_ip = self.device_1_ip if device_num == 1 else self.device_2_ip
            device_port = self.device_1_port if device_num == 1 else self.device_2_port

            if not conn:
                return {}

            return {
                "device_num":        device_num,
                "device_type":       "IN Device" if device_num == 1 else "OUT Device",
                "ip":                device_ip,
                "port":              device_port,
                "firmware_version":  conn.get_firmware_version(),
                "serial_number":     conn.get_serialnumber(),
                "platform":          conn.get_platform(),
                "device_name":       conn.get_device_name(),
                "mac_address":       conn.get_mac(),
            }
        except Exception as e:
            print(f"❌ Error getting Device {device_num} info: {e}")
            return {}

    def full_sync(self) -> Dict:
        """
        Full dual-device synchronization.

        Acquires _ZK_LOCK to prevent concurrent connections.
        Syncs both devices sequentially.
        """
        result = {
            "status":               "success",
            "timestamp":            datetime.utcnow().isoformat(),
            "users":                {},
            "logs":                 {},
            "processed_attendance": {},
            "device_1_info":        {},
            "device_2_info":        {},
        }

        # Acquire lock with timeout
        if not _ZK_LOCK.acquire(timeout=60):
            result["status"] = "failed"
            result["error"]  = "Device busy — another sync is in progress"
            print("⚠️  Sync skipped — device lock not acquired within 60s")
            return result

        try:
            print("\n" + "=" * 80)
            print("🚀 Starting DUAL DEVICE SYNC")
            print("=" * 80)

            # Connect to both devices
            dev1_connected = self.connect_device(1, disable=True)
            dev2_connected = self.connect_device(2, disable=True)

            if not (dev1_connected or dev2_connected):
                result["status"] = "failed"
                result["error"]  = "Failed to connect to any device"
                return result

            # Get device info
            result["device_1_info"] = self.get_device_info(1)
            result["device_2_info"] = self.get_device_info(2)

            # Sync users from both devices
            result["users"] = self.sync_users()

            # Sync attendance logs from both devices
            result["logs"] = self.sync_attendance_logs()

            # Process attendance
            processor = AttendanceProcessor(self.db)
            result["processed_attendance"] = processor.process_all_pending()

            self._log_sync_status("success", "Dual device sync completed successfully")
            print("\n✅ Dual device synchronization completed successfully!")
            print("=" * 80 + "\n")

        except Exception as e:
            result["status"] = "failed"
            result["error"]  = str(e)
            self._log_sync_status("failed", str(e))
            print(f"\n❌ Sync failed: {e}")

        finally:
            self.disconnect_device(1)
            self.disconnect_device(2)
            _ZK_LOCK.release()

        return result

    def get_info_safe(self) -> Dict:
        """
        Read-only device info check for both devices.
        Does NOT disable the devices — safe to call frequently.
        """
        if not _ZK_LOCK.acquire(timeout=5):
            return {}

        try:
            info = {"device_1": {}, "device_2": {}}

            if self.connect_device(1, disable=False):
                info["device_1"] = self.get_device_info(1)

            if self.connect_device(2, disable=False):
                info["device_2"] = self.get_device_info(2)

            return info
        except Exception as e:
            print(f"❌ Info check failed: {e}")
            return {}
        finally:
            self.disconnect_device(1)
            self.disconnect_device(2)
            _ZK_LOCK.release()

    def _log_sync_status(self, status: str, message: str):
        """Log sync status to database."""
        try:
            if len(message) > 500:
                message = message[:497] + "..."

            # Log for Device 1
            device_1 = self.db.query(Device).filter(
                Device.device_ip == self.device_1_ip
            ).first()

            if not device_1:
                device_1 = Device(
                    device_ip=self.device_1_ip,
                    device_port=self.device_1_port,
                )
                self.db.add(device_1)

            device_1.last_sync_at      = datetime.utcnow()
            device_1.last_sync_status  = status
            device_1.last_sync_message = message

            # Log for Device 2
            device_2 = self.db.query(Device).filter(
                Device.device_ip == self.device_2_ip
            ).first()

            if not device_2:
                device_2 = Device(
                    device_ip=self.device_2_ip,
                    device_port=self.device_2_port,
                )
                self.db.add(device_2)

            device_2.last_sync_at      = datetime.utcnow()
            device_2.last_sync_status  = status
            device_2.last_sync_message = message

            self.db.commit()

        except Exception as e:
            print(f"⚠️ Error logging sync status: {e}")
            self.db.rollback()
