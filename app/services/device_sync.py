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
        - Match ONLY on uid (device slot number) — never on user_id_str or name.
        - If uid exists on device AND in DB with same name → update fields only.
        - If uid exists on device BUT DB row has a DIFFERENT name (uid reused by
          new person) → retire the old row, create a fresh row for the new person.
        - If uid exists on device but NOT in DB at all → create new row.
        - If uid is in DB (active) but NOT on device → deactivate it.
        - NEVER reactivate a retired/deleted row — if the old row is inactive and
          the device sends the same uid with a different name, create a NEW row.
        """
        try:
            device_users = self.conn.get_users()
            device_uids  = {u.uid for u in device_users}

            added_count       = 0
            updated_count     = 0
            deactivated_count = 0
            retired_count     = 0

            for device_user in device_users:
                # Find ANY existing row for this uid (active or not)
                existing = self.db.query(User).filter(
                    User.uid == device_user.uid
                ).first()

                if existing:
                    # ── Same uid, same person (names match) ──────────────── #
                    if existing.name.strip().lower() == device_user.name.strip().lower():
                        # Just update fields, always keep active
                        existing.privilege    = device_user.privilege
                        existing.password     = device_user.password
                        existing.group_id     = device_user.group_id
                        existing.user_id_str  = str(device_user.user_id)
                        existing.card_no      = str(device_user.card) if device_user.card else None
                        existing.is_active    = True
                        existing.updated_at   = datetime.utcnow()
                        updated_count += 1
                        print(f"✅ Updated UID {device_user.uid} — {device_user.name}")

                    else:
                        # ── Same uid, DIFFERENT person — uid was reused ───── #
                        # Retire the old row permanently (prefix name so it's
                        # obvious and never accidentally reactivated)
                        old_name = existing.name
                        existing.is_active  = False
                        existing.name       = f"[RETIRED] {existing.name}"
                        existing.updated_at = datetime.utcnow()
                        retired_count += 1
                        print(f"⚠️  Retired old UID {device_user.uid} ({old_name}) — reused by {device_user.name}")

                        # Create a fresh row for the new person at this uid
                        new_user = User(
                            uid          = device_user.uid,
                            name         = device_user.name,
                            privilege    = device_user.privilege,
                            password     = device_user.password,
                            group_id     = device_user.group_id,
                            user_id_str  = str(device_user.user_id),
                            card_no      = str(device_user.card) if device_user.card else None,
                            is_active    = True,
                        )
                        self.db.add(new_user)
                        added_count += 1
                        print(f"✅ Created new row for UID {device_user.uid} — {device_user.name}")

                else:
                    # ── uid not in DB at all → create ────────────────────── #
                    new_user = User(
                        uid          = device_user.uid,
                        name         = device_user.name,
                        privilege    = device_user.privilege,
                        password     = device_user.password,
                        group_id     = device_user.group_id,
                        user_id_str  = str(device_user.user_id),
                        card_no      = str(device_user.card) if device_user.card else None,
                        is_active    = True,
                    )
                    self.db.add(new_user)
                    added_count += 1
                    print(f"➕ Added new UID {device_user.uid} — {device_user.name}")

            # ── Deactivate DB users whose uid is no longer on device ──── #
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
        try:
            logs = self.conn.get_attendance()
            new_count = 0
            duplicate_count = 0
            error_count = 0
            skipped_count = 0

            # Build a set of all known UIDs in the users table to avoid
            # ForeignKeyViolation when a device log references a UID that
            # was never synced (e.g. deleted/missing user with UID 4).
            known_uids = {
                row[0]
                for row in self.db.query(User.uid).all()
            }

            for device_log in logs:
                try:
                    # Skip logs whose UID has no matching user row
                    if device_log.user_id not in known_uids:
                        skipped_count += 1
                        continue

                    existing = self.db.query(AttendanceLog).filter(
                        AttendanceLog.uid == device_log.user_id,
                        AttendanceLog.timestamp == device_log.timestamp
                    ).first()

                    if existing:
                        duplicate_count += 1
                        continue

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
                "skipped_unknown_uid": skipped_count,
                "errors": error_count
            }

            print(
                f"📋 Logs synced — Total: {len(logs)}, New: {new_count}, "
                f"Duplicates: {duplicate_count}, Skipped (unknown UID): {skipped_count}"
            )
            return result

        except Exception as e:
            self.db.rollback()
            print(f"❌ Error syncing attendance logs: {e}")
            raise

    def get_device_info(self) -> Dict:
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

            result["device_info"] = self.get_device_info()
            result["users"] = self.sync_users()
            result["logs"] = self.sync_attendance_logs()

            processor = AttendanceProcessor(self.db)
            result["processed_attendance"] = processor.process_all_pending()

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
        try:
            # VARCHAR(500) limit — truncate long messages (e.g. full exception traces)
            if len(message) > 500:
                message = message[:497] + "..."

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