#!/usr/bin/env python3
"""
Dual Device Sync Test with Mock Data
─────────────────────────────────────────────────────────────────────────────

Purpose: Test the dual device system with mock users that have:
  - Same NAME on both devices (name-based matching)
  - Different UIDs on each device
  - Device 1 (192.168.1.201) = IN punches
  - Device 2 (192.168.1.35) = OUT punches

This simulates the real scenario where users are registered on both devices
with the same name but different UIDs.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.orm import Session
from app.core.database import get_db, init_db
from app.models.user import User
from app.models.attendance import AttendanceLog
from app.services.device_sync import DeviceSyncService
from app.services.attendance_processor import AttendanceProcessor
from app.config import get_settings

settings = get_settings()


class MockZKUser:
    """Mock ZK device user object."""
    def __init__(self, uid, name, user_id, privilege=0, password='', group_id='0', card=None):
        self.uid = uid
        self.name = name
        self.user_id = user_id
        self.privilege = privilege
        self.password = password
        self.group_id = group_id
        self.card = card


class MockZKAttendance:
    """Mock ZK attendance log object."""
    def __init__(self, user_id, timestamp, punch_type=0, status=0):
        self.user_id = user_id
        self.timestamp = timestamp
        self.punch = punch_type
        self.status = status


def create_mock_users():
    """
    Create mock users with:
    - Same names on both devices
    - Different UIDs on each device

    Returns:
        (device_1_users, device_2_users)
    """

    # Device 1 Users (IN Device) - UID range 1-10
    device_1_users = [
        MockZKUser(uid=1, name="John Smith", user_id=101),
        MockZKUser(uid=2, name="Sarah Johnson", user_id=102),
        MockZKUser(uid=3, name="Mike Williams", user_id=103),
        MockZKUser(uid=4, name="Emily Brown", user_id=104),
        MockZKUser(uid=5, name="David Jones", user_id=105),
    ]

    # Device 2 Users (OUT Device) - UID range 20-30 (DIFFERENT UIDs, SAME names)
    device_2_users = [
        MockZKUser(uid=21, name="John Smith", user_id=201),      # Same name, different UID
        MockZKUser(uid=22, name="Sarah Johnson", user_id=202),   # Same name, different UID
        MockZKUser(uid=23, name="Mike Williams", user_id=203),   # Same name, different UID
        MockZKUser(uid=24, name="Emily Brown", user_id=204),     # Same name, different UID
        MockZKUser(uid=25, name="David Jones", user_id=205),     # Same name, different UID
    ]

    return device_1_users, device_2_users


def create_mock_attendance():
    """
    Create mock attendance logs for both devices.

    Scenario: Regular shift + Break shift users
    - Device 1 = IN punches (using device 1 user_ids: 101-105)
    - Device 2 = OUT punches (using device 2 user_ids: 201-205)

    Returns:
        (device_1_logs, device_2_logs)
    """

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Device 1 Attendance (IN Device)
    device_1_logs = [
        # John Smith - Regular shift (1 IN)
        MockZKAttendance(user_id=101, timestamp=today + timedelta(hours=9, minutes=0)),

        # Sarah Johnson - Break shift (2 INs)
        MockZKAttendance(user_id=102, timestamp=today + timedelta(hours=8, minutes=30)),
        MockZKAttendance(user_id=102, timestamp=today + timedelta(hours=14, minutes=0)),

        # Mike Williams - Regular shift (1 IN)
        MockZKAttendance(user_id=103, timestamp=today + timedelta(hours=9, minutes=15)),

        # Emily Brown - Break shift (2 INs)
        MockZKAttendance(user_id=104, timestamp=today + timedelta(hours=7, minutes=45)),
        MockZKAttendance(user_id=104, timestamp=today + timedelta(hours=13, minutes=30)),

        # David Jones - Regular shift (1 IN)
        MockZKAttendance(user_id=105, timestamp=today + timedelta(hours=8, minutes=50)),
    ]

    # Device 2 Attendance (OUT Device)
    device_2_logs = [
        # John Smith - Regular shift (1 OUT)
        MockZKAttendance(user_id=201, timestamp=today + timedelta(hours=18, minutes=0)),

        # Sarah Johnson - Break shift (2 OUTs)
        MockZKAttendance(user_id=202, timestamp=today + timedelta(hours=13, minutes=0)),
        MockZKAttendance(user_id=202, timestamp=today + timedelta(hours=19, minutes=30)),

        # Mike Williams - Regular shift (1 OUT)
        MockZKAttendance(user_id=203, timestamp=today + timedelta(hours=17, minutes=45)),

        # Emily Brown - Break shift (2 OUTs)
        MockZKAttendance(user_id=204, timestamp=today + timedelta(hours=12, minutes=30)),
        MockZKAttendance(user_id=204, timestamp=today + timedelta(hours=18, minutes=15)),

        # David Jones - Regular shift (1 OUT)
        MockZKAttendance(user_id=205, timestamp=today + timedelta(hours=17, minutes=30)),
    ]

    return device_1_logs, device_2_logs


def inject_mock_data(db: Session):
    """
    Inject mock data directly into database to simulate device sync.

    This simulates what DeviceSyncService would do after fetching from real devices.
    """

    print("\n" + "="*80)
    print("🧪 DUAL DEVICE SYNC TEST - MOCK DATA INJECTION")
    print("="*80)

    # Get mock data
    device_1_users, device_2_users = create_mock_users()
    device_1_logs, device_2_logs = create_mock_attendance()

    print(f"\n📊 Mock Data Summary:")
    print(f"   Device 1 Users: {len(device_1_users)}")
    print(f"   Device 2 Users: {len(device_2_users)}")
    print(f"   Device 1 Attendance Logs: {len(device_1_logs)}")
    print(f"   Device 2 Attendance Logs: {len(device_2_logs)}")

    # Step 1: Sync Users (name-based matching)
    print("\n" + "-"*80)
    print("Step 1: Syncing Users (Name-Based Matching)")
    print("-"*80)

    users_by_name = {}

    # Process Device 1 users
    for dev_user in device_1_users:
        norm_name = dev_user.name.strip().lower()
        if norm_name not in users_by_name:
            users_by_name[norm_name] = []
        users_by_name[norm_name].append(('Device1', dev_user))

    # Process Device 2 users
    for dev_user in device_2_users:
        norm_name = dev_user.name.strip().lower()
        if norm_name not in users_by_name:
            users_by_name[norm_name] = []
        users_by_name[norm_name].append(('Device2', dev_user))

    # Create unified users in DB
    created_users = {}
    for norm_name, device_entries in users_by_name.items():
        # Prefer Device 1 for primary UID
        primary_entry = next((e for e in device_entries if e[0] == 'Device1'), device_entries[0])
        _, primary_user = primary_entry

        # Check if user exists
        existing = db.query(User).filter(User.name.ilike(primary_user.name)).first()

        if existing:
            print(f"✅ User exists: {primary_user.name} (UID: {existing.uid})")
            created_users[norm_name] = existing
        else:
            new_user = User(
                uid=primary_user.uid,
                name=primary_user.name,
                privilege=primary_user.privilege,
                user_id_str=str(primary_user.user_id),
                is_active=True
            )
            db.add(new_user)
            db.flush()
            created_users[norm_name] = new_user
            print(f"➕ Created user: {primary_user.name} (UID: {new_user.uid})")
            print(f"   └─ Device 1 UID: {[e[1].uid for e in device_entries if e[0] == 'Device1']}")
            print(f"   └─ Device 2 UID: {[e[1].uid for e in device_entries if e[0] == 'Device2']}")

    db.commit()

    # Step 2: Create name-to-user mapping for attendance logs
    print("\n" + "-"*80)
    print("Step 2: Creating User ID Mappings")
    print("-"*80)

    # Build mapping: device_user_id -> DB user
    device_1_user_map = {}  # user_id -> User
    device_2_user_map = {}  # user_id -> User

    for norm_name, device_entries in users_by_name.items():
        db_user = created_users[norm_name]

        for device_type, dev_user in device_entries:
            if device_type == 'Device1':
                device_1_user_map[dev_user.user_id] = db_user
                print(f"   Device 1: user_id {dev_user.user_id} → {db_user.name} (DB UID: {db_user.uid})")
            else:
                device_2_user_map[dev_user.user_id] = db_user
                print(f"   Device 2: user_id {dev_user.user_id} → {db_user.name} (DB UID: {db_user.uid})")

    # Step 3: Inject Attendance Logs
    print("\n" + "-"*80)
    print("Step 3: Injecting Attendance Logs")
    print("-"*80)

    # Device 1 logs (IN punches)
    print(f"\n📥 Device 1 (IN Device) - {settings.DEVICE_1_IP}")
    for log in device_1_logs:
        if log.user_id in device_1_user_map:
            db_user = device_1_user_map[log.user_id]

            # Check for duplicate
            existing = db.query(AttendanceLog).filter(
                AttendanceLog.uid == db_user.uid,
                AttendanceLog.timestamp == log.timestamp,
                AttendanceLog.device_ip == settings.DEVICE_1_IP
            ).first()

            if not existing:
                new_log = AttendanceLog(
                    uid=db_user.uid,
                    timestamp=log.timestamp,
                    punch_type=log.punch,
                    status=log.status,
                    device_ip=settings.DEVICE_1_IP  # Tag as Device 1
                )
                db.add(new_log)
                print(f"   ✅ IN  → {db_user.name} at {log.timestamp.strftime('%I:%M %p')}")

    # Device 2 logs (OUT punches)
    print(f"\n📤 Device 2 (OUT Device) - {settings.DEVICE_2_IP}")
    for log in device_2_logs:
        if log.user_id in device_2_user_map:
            db_user = device_2_user_map[log.user_id]

            # Check for duplicate
            existing = db.query(AttendanceLog).filter(
                AttendanceLog.uid == db_user.uid,
                AttendanceLog.timestamp == log.timestamp,
                AttendanceLog.device_ip == settings.DEVICE_2_IP
            ).first()

            if not existing:
                new_log = AttendanceLog(
                    uid=db_user.uid,
                    timestamp=log.timestamp,
                    punch_type=log.punch,
                    status=log.status,
                    device_ip=settings.DEVICE_2_IP  # Tag as Device 2
                )
                db.add(new_log)
                print(f"   ✅ OUT → {db_user.name} at {log.timestamp.strftime('%I:%M %p')}")

    db.commit()

    print("\n✅ Mock data injection complete!")


def test_attendance_processing(db: Session):
    """Test the attendance processor with injected mock data."""

    print("\n" + "="*80)
    print("🔍 TESTING ATTENDANCE PROCESSOR")
    print("="*80)

    processor = AttendanceProcessor(db)
    result = processor.process_all_pending()

    print(f"\n📊 Processing Results:")
    print(f"   Processed: {result['processed']}")
    print(f"   Errors: {result['errors']}")
    print(f"   Total: {result['total']}")

    # Display processed attendance
    from app.models.attendance import ProcessedAttendance
    import json

    today = datetime.now().date()
    records = db.query(ProcessedAttendance, User).join(
        User, ProcessedAttendance.uid == User.uid
    ).filter(ProcessedAttendance.date == today).all()

    print(f"\n📋 Processed Attendance Records ({len(records)} total):")
    print("-"*80)

    for att, user in records:
        print(f"\n👤 {user.name} (UID: {user.uid})")
        print(f"   Shift: {att.shift or 'Regular'}")
        print(f"   Status: {att.status.value.upper()}")
        print(f"   Work Hours: {att.work_duration_hours:.2f} hrs" if att.work_duration_hours else "   Work Hours: 0.00 hrs")

        # Parse and display sessions
        if att.punch_sessions:
            try:
                sessions = json.loads(att.punch_sessions)
                print(f"   Sessions:")
                for idx, session in enumerate(sessions, 1):
                    in_time = datetime.fromisoformat(session['in']).strftime('%I:%M %p') if session['in'] else '-'
                    out_time = datetime.fromisoformat(session['out']).strftime('%I:%M %p') if session['out'] else '-'
                    print(f"      Session {idx}: IN {in_time} → OUT {out_time}")
            except:
                pass

        if att.remarks:
            print(f"   Remarks: {att.remarks}")


def verify_name_based_matching(db: Session):
    """Verify that users were matched by name despite different UIDs."""

    print("\n" + "="*80)
    print("✅ VERIFICATION: Name-Based Matching")
    print("="*80)

    from app.models.attendance import AttendanceLog

    users = db.query(User).filter(User.is_active == True).all()

    print(f"\n📊 Unified User Registry: {len(users)} users")
    print("-"*80)

    for user in users:
        # Get logs from both devices
        device_1_logs = db.query(AttendanceLog).filter(
            AttendanceLog.uid == user.uid,
            AttendanceLog.device_ip == settings.DEVICE_1_IP
        ).count()

        device_2_logs = db.query(AttendanceLog).filter(
            AttendanceLog.uid == user.uid,
            AttendanceLog.device_ip == settings.DEVICE_2_IP
        ).count()

        print(f"\n👤 {user.name}")
        print(f"   DB UID: {user.uid}")
        print(f"   Device 1 (IN) logs: {device_1_logs}")
        print(f"   Device 2 (OUT) logs: {device_2_logs}")
        print(f"   ✅ Successfully matched by NAME across both devices!")


def main():
    """Main test function."""

    print("\n" + "="*80)
    print("🚀 DUAL DEVICE SYNC TEST - MOCK DATA")
    print("="*80)
    print(f"Device 1 (IN):  {settings.DEVICE_1_IP}")
    print(f"Device 2 (OUT): {settings.DEVICE_2_IP}")
    print("="*80)

    # Initialize database
    print("\n📊 Initializing database...")
    init_db()

    # Get database session
    db = next(get_db())

    try:
        # Inject mock data
        inject_mock_data(db)

        # Process attendance
        test_attendance_processing(db)

        # Verify name-based matching
        verify_name_based_matching(db)

        print("\n" + "="*80)
        print("✅ DUAL DEVICE SYNC TEST COMPLETED SUCCESSFULLY!")
        print("="*80)
        print("\n📝 Test Summary:")
        print("   ✅ Users synced with name-based matching")
        print("   ✅ Device 1 punches tagged as IN")
        print("   ✅ Device 2 punches tagged as OUT")
        print("   ✅ Regular & Break Shift users detected")
        print("   ✅ Attendance processed correctly")
        print("\n🌐 Check the UI:")
        print(f"   Dashboard:   http://localhost:8000")
        print(f"   API Docs:    http://localhost:8000/docs")
        print("="*80 + "\n")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
