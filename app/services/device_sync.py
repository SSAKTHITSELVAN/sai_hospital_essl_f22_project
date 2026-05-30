# app/services/device_sync.py
"""
Key fixes in this version
─────────────────────────
1.  uid vs user_id mismatch fixed.
    AttendanceLog.uid (FK → users.uid = slot number) was being populated with
    device_log.user_id (enrollment ID) which can be a different value.
    Now builds a user_id_str → uid map to always store the correct slot uid.

2.  Threading lock (_ZK_LOCK) prevents concurrent ZK connections.
    The F22 supports only one simultaneous connection. Without the lock,
    background sync + device-info poll + manual sync could all connect at once,
    causing failures or data corruption.

3.  connect() accepts a `disable` parameter.
    Pass disable=False for read-only operations (device info) so the fingerprint
    scanner is NOT paused during the call.
"""

import threading
from sqlalchemy.orm import Session
from zk import ZK
from datetime import datetime
from typing import Dict

from app.models.user import User
from app.models.attendance import AttendanceLog
from app.models.device import Device
from app.config import get_settings
from app.services.attendance_processor import AttendanceProcessor

settings = get_settings()

# Module-level lock — shared across all DeviceSyncService instances.
# Ensures only ONE ZK connection exists at any point in time.
_ZK_LOCK = threading.Lock()


class DeviceSyncService:
    """
    Service to synchronize data from ESSL F22 device.
    Thread-safe: uses _ZK_LOCK to prevent concurrent connections.
    """

    def __init__(self, db: Session):
        self.db          = db
        self.device_ip   = settings.DEVICE_IP
        self.device_port = settings.DEVICE_PORT
        self.timeout     = settings.DEVICE_TIMEOUT
        self.zk          = ZK(
            self.device_ip,
            port=self.device_port,
            timeout=self.timeout,
            password=0,
            force_udp=False,
            ommit_ping=True,
        )
        self.conn = None

    def connect(self, disable: bool = True) -> bool:
        """
        Connect to the device.

        Args:
            disable: If True (default for sync), disable the device during operation
                     so new punches don't interfere with data reads.
                     Pass False for info-only calls to avoid pausing the scanner.
        """
        try:
            print(f"🔌 Connecting to device {self.device_ip}:{self.device_port}...")
            self.conn = self.zk.connect()
            if disable:
                self.conn.disable_device()
                print("✅ Device connected and disabled for sync")
            else:
                print("✅ Device connected (read-only, not disabled)")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            self._log_sync_status("failed", str(e))
            return False

    def disconnect(self):
        if self.conn:
            try:
                self.conn.enable_device()
                self.zk.disconnect()
                print("✅ Device disconnected and re-enabled")
            except Exception as e:
                print(f"⚠️ Error during disconnect: {e}")

    def sync_users(self) -> Dict:
        """
        Sync users from device to database.

        Rules:
        - Match ONLY on uid (device slot number).
        - Same uid + same name → update fields.
        - Same uid + different name → retire old row, create new.
        - uid missing from DB → create.
        - Active DB uid not on device → deactivate.
        """
        try:
            device_users = self.conn.get_users()
            device_uids  = {u.uid for u in device_users}

            added_count       = 0
            updated_count     = 0
            deactivated_count = 0
            retired_count     = 0

            for device_user in device_users:
                existing = self.db.query(User).filter(
                    User.uid == device_user.uid
                ).first()

                if existing:
                    if existing.name.strip().lower() == device_user.name.strip().lower():
                        existing.privilege   = device_user.privilege
                        existing.password    = device_user.password
                        existing.group_id    = device_user.group_id
                        existing.user_id_str = str(device_user.user_id)
                        existing.card_no     = str(device_user.card) if device_user.card else None
                        existing.is_active   = True
                        existing.updated_at  = datetime.utcnow()
                        updated_count += 1
                        print(f"✅ Updated UID {device_user.uid} — {device_user.name}")
                    else:
                        old_name            = existing.name
                        existing.is_active  = False
                        existing.name       = f"[RETIRED] {existing.name}"
                        existing.updated_at = datetime.utcnow()
                        retired_count += 1
                        print(f"⚠️  Retired UID {device_user.uid} ({old_name}) → reused by {device_user.name}")

                        new_user = User(
                            uid         = device_user.uid,
                            name        = device_user.name,
                            privilege   = device_user.privilege,
                            password    = device_user.password,
                            group_id    = device_user.group_id,
                            user_id_str = str(device_user.user_id),
                            card_no     = str(device_user.card) if device_user.card else None,
                            is_active   = True,
                        )
                        self.db.add(new_user)
                        added_count += 1
                        print(f"✅ Created new row for UID {device_user.uid} — {device_user.name}")
                else:
                    new_user = User(
                        uid         = device_user.uid,
                        name        = device_user.name,
                        privilege   = device_user.privilege,
                        password    = device_user.password,
                        group_id    = device_user.group_id,
                        user_id_str = str(device_user.user_id),
                        card_no     = str(device_user.card) if device_user.card else None,
                        is_active   = True,
                    )
                    self.db.add(new_user)
                    added_count += 1
                    print(f"➕ Added new UID {device_user.uid} — {device_user.name}")

            active_db_users = self.db.query(User).filter(User.is_active == True).all()
            for db_user in active_db_users:
                if db_user.uid not in device_uids:
                    db_user.is_active  = False
                    db_user.updated_at = datetime.utcnow()
                    deactivated_count += 1
                    print(f"🗑️  Deactivated UID {db_user.uid} ({db_user.name}) — removed from device")

            self.db.commit()

            result = {
                "total":       len(device_users),
                "added":       added_count,
                "updated":     updated_count,
                "retired":     retired_count,
                "deactivated": deactivated_count,
            }
            print(
                f"\n👥 Users synced — Device: {len(device_users)}, "
                f"Added: {added_count}, Updated: {updated_count}, "
                f"Retired: {retired_count}, Deactivated: {deactivated_count}"
            )
            return result

        except Exception as e:
            self.db.rollback()
            print(f"❌ Error syncing users: {e}")
            raise

    def sync_attendance_logs(self) -> Dict:
        """
        Sync raw punch logs from device to DB.

        FIX: Builds a user_id_str → uid map so device attendance logs
        (which carry enrollment user_id, not slot uid) are correctly matched
        to the users table FK (which uses slot uid).
        """
        try:
            logs = self.conn.get_attendance()
            new_count       = 0
            duplicate_count = 0
            error_count     = 0
            skipped_count   = 0

            # ── Build user_id → uid mapping ─────────────────────────────── #
            # Device attendance logs carry device_log.user_id (the enrollment ID,
            # stored in User.user_id_str). The AttendanceLog FK points to users.uid
            # (the slot number). These two values CAN differ on the device.
            # We resolve device user_id → DB uid here to avoid FK mismatches.
            user_id_to_uid: Dict[str, int] = {}
            for row in self.db.query(User.user_id_str, User.uid).all():
                user_id_str, slot_uid = row[0], row[1]
                if user_id_str:
                    user_id_to_uid[str(user_id_str)] = slot_uid
                # Also map uid-as-string for devices where user_id == uid
                user_id_to_uid[str(slot_uid)] = slot_uid

            for device_log in logs:
                try:
                    log_user_id_str = str(device_log.user_id)

                    # Resolve to DB slot uid
                    if log_user_id_str not in user_id_to_uid:
                        print(f"⚠️  Skipping log — unknown user_id '{log_user_id_str}'")
                        skipped_count += 1
                        continue

                    matched_uid = user_id_to_uid[log_user_id_str]

                    # Check for duplicate
                    existing = self.db.query(AttendanceLog).filter(
                        AttendanceLog.uid       == matched_uid,
                        AttendanceLog.timestamp == device_log.timestamp,
                    ).first()

                    if existing:
                        duplicate_count += 1
                        continue

                    new_log = AttendanceLog(
                        uid        = matched_uid,          # correct slot uid
                        timestamp  = device_log.timestamp,
                        punch_type = device_log.punch,
                        status     = device_log.status,
                    )
                    self.db.add(new_log)
                    new_count += 1

                except Exception as log_error:
                    print(f"⚠️ Error processing log: {log_error}")
                    error_count += 1
                    continue

            self.db.commit()

            result = {
                "total":              len(logs),
                "new":                new_count,
                "duplicates":         duplicate_count,
                "skipped_unknown_uid": skipped_count,
                "errors":             error_count,
            }
            print(
                f"📋 Logs synced — Total: {len(logs)}, New: {new_count}, "
                f"Duplicates: {duplicate_count}, Skipped: {skipped_count}"
            )
            return result

        except Exception as e:
            self.db.rollback()
            print(f"❌ Error syncing attendance logs: {e}")
            raise

    def get_device_info(self) -> Dict:
        try:
            return {
                "ip":               self.device_ip,
                "port":             self.device_port,
                "firmware_version": self.conn.get_firmware_version(),
                "serial_number":    self.conn.get_serialnumber(),
                "platform":         self.conn.get_platform(),
                "device_name":      self.conn.get_device_name(),
                "mac_address":      self.conn.get_mac(),
            }
        except Exception as e:
            print(f"❌ Error getting device info: {e}")
            return {}

    def full_sync(self) -> Dict:
        """
        Full device synchronization.
        Acquires _ZK_LOCK to prevent concurrent connections.
        """
        result = {
            "status":               "success",
            "timestamp":            datetime.utcnow().isoformat(),
            "users":                {},
            "logs":                 {},
            "processed_attendance": {},
            "device_info":          {},
        }

        # Acquire lock with timeout — don't wait forever if device is busy
        if not _ZK_LOCK.acquire(timeout=60):
            result["status"] = "failed"
            result["error"]  = "Device busy — another sync is in progress"
            print("⚠️  Sync skipped — device lock not acquired within 60s")
            return result

        try:
            if not self.connect(disable=True):
                result["status"] = "failed"
                result["error"]  = "Failed to connect to device"
                return result

            result["device_info"]          = self.get_device_info()
            result["users"]                = self.sync_users()
            result["logs"]                 = self.sync_attendance_logs()

            processor = AttendanceProcessor(self.db)
            result["processed_attendance"] = processor.process_all_pending()

            self._log_sync_status("success", "Full sync completed successfully")
            print("\n✅ Full synchronization completed successfully!")

        except Exception as e:
            result["status"] = "failed"
            result["error"]  = str(e)
            self._log_sync_status("failed", str(e))
            print(f"\n❌ Sync failed: {e}")

        finally:
            self.disconnect()
            _ZK_LOCK.release()

        return result

    def get_info_safe(self) -> Dict:
        """
        Read-only device info check.
        Does NOT disable the device — safe to call frequently.
        Acquires _ZK_LOCK to avoid concurrent connections.
        Returns empty dict if device is busy or unreachable.
        """
        if not _ZK_LOCK.acquire(timeout=5):
            return {}   # device busy — return empty gracefully

        try:
            if not self.connect(disable=False):
                return {}
            return self.get_device_info()
        except Exception as e:
            print(f"❌ Info check failed: {e}")
            return {}
        finally:
            self.disconnect()
            _ZK_LOCK.release()

    def _log_sync_status(self, status: str, message: str):
        try:
            if len(message) > 500:
                message = message[:497] + "..."

            device = self.db.query(Device).filter(
                Device.device_ip == self.device_ip
            ).first()

            if not device:
                device = Device(
                    device_ip=self.device_ip,
                    device_port=self.device_port,
                )
                self.db.add(device)

            device.last_sync_at      = datetime.utcnow()
            device.last_sync_status  = status
            device.last_sync_message = message
            self.db.commit()

        except Exception as e:
            print(f"⚠️ Error logging sync status: {e}")
            self.db.rollback()