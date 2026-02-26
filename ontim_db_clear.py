"""
fix_db_to_match_device.py
--------------------------
ONE-TIME script to make your PostgreSQL users table exactly match
what the device currently has enrolled.

Run ONCE after deploying the new device_sync.py:
    python3 fix_db_to_match_device.py

What it does:
  1. Connects to the ESSL F22 device and fetches live user list
  2. Reassigns attendance_logs and processed_attendance for mismatched UIDs
     (e.g. moves uid=2 logs → uid=24 for Bharanilakshmi)
  3. Deactivates all DB users not present on device
  4. Updates all active users to match device name/privilege/user_id_str exactly
  5. Prints a full reconciliation report
"""

import sys
from datetime import datetime
from zk import ZK
import psycopg2
import psycopg2.extras

# ── Configure these ────────────────────────────────────────────────────── #
DEVICE_IP   = "192.168.1.100"   # your device IP
DEVICE_PORT = 4370

DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "your_db_name"
DB_USER = "your_db_user"
DB_PASS = "your_db_password"
# ────────────────────────────────────────────────────────────────────────── #


def get_device_users():
    zk   = ZK(DEVICE_IP, port=DEVICE_PORT, timeout=30, password=0, force_udp=False, ommit_ping=True)
    conn = None
    try:
        print(f"Connecting to device {DEVICE_IP}:{DEVICE_PORT} ...")
        conn = zk.connect()
        conn.disable_device()
        users = conn.get_users()
        print(f"Got {len(users)} users from device.\n")
        return users
    finally:
        if conn:
            conn.enable_device()
            zk.disconnect()


def run():
    device_users  = get_device_users()
    device_uid_map = {u.uid: u for u in device_users}  # uid → device user

    db = psycopg2.connect(
        host=DB_HOST, port=DB_PORT,
        dbname=DB_NAME, user=DB_USER, password=DB_PASS
    )
    db.autocommit = False
    cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)

    try:
        # ── Step 1: Get all DB users ─────────────────────────────────── #
        cur.execute("SELECT id, uid, name, user_id_str, is_active FROM users ORDER BY uid")
        db_users = cur.fetchall()
        db_uid_map = {row["uid"]: row for row in db_users}

        print("=" * 60)
        print("RECONCILIATION PLAN")
        print("=" * 60)

        # ── Step 2: Find uid collisions ──────────────────────────────── #
        # Case: DB has uid=X inactive, device has uid=X with different person
        # We need to check if any active device uid has logs under a wrong uid
        # 
        # Known case from your data:
        #   DB uid=2  (Sridevigadmin, inactive) has logs that belong to uid=24
        #   DB uid=4  (Malarvizhi,    inactive) has logs that belong to uid=25
        #   DB uid=9  (Arsath,        inactive) has logs that belong to uid=26
        #
        # Detect: for each inactive DB uid, find which active device user
        # has user_id_str matching the inactive user's user_id_str
        
        reassignments = []  # list of (from_uid, to_uid, reason)

        for db_row in db_users:
            db_uid = db_row["uid"]
            if db_row["is_active"]:
                continue  # only check inactive rows
            
            # Check if any device user has same user_id_str
            for dev_uid, du in device_uid_map.items():
                if str(du.user_id) == str(db_row["user_id_str"]) and dev_uid != db_uid:
                    reassignments.append({
                        "from_uid":    db_uid,
                        "to_uid":      dev_uid,
                        "old_name":    db_row["name"],
                        "new_name":    du.name,
                        "user_id_str": str(du.user_id),
                    })
                    print(f"  REASSIGN logs: uid={db_uid} ({db_row['name']}) "
                          f"→ uid={dev_uid} ({du.name})  [display_id={du.user_id}]")

        if not reassignments:
            print("  No log reassignments needed.")

        # ── Step 3: Apply log reassignments ─────────────────────────── #
        for r in reassignments:
            print(f"\nMoving attendance_logs uid={r['from_uid']} → {r['to_uid']} ...")
            cur.execute(
                "UPDATE attendance_logs SET uid = %s WHERE uid = %s",
                (r["to_uid"], r["from_uid"])
            )
            rows = cur.rowcount
            print(f"  {rows} attendance_log rows moved")

            cur.execute(
                "UPDATE processed_attendance SET uid = %s WHERE uid = %s",
                (r["to_uid"], r["from_uid"])
            )
            rows = cur.rowcount
            print(f"  {rows} processed_attendance rows moved")

        # ── Step 4: Deactivate all DB uids not on device ────────────── #
        print("\nDeactivating DB users not present on device ...")
        for db_uid, db_row in db_uid_map.items():
            if db_uid not in device_uid_map and db_row["is_active"]:
                cur.execute(
                    "UPDATE users SET is_active = false, updated_at = %s WHERE uid = %s",
                    (datetime.utcnow(), db_uid)
                )
                print(f"  Deactivated uid={db_uid} ({db_row['name']})")

        # ── Step 5: Upsert device users into DB ──────────────────────── #
        print("\nUpdating/inserting device users into DB ...")
        for uid, du in device_uid_map.items():
            if uid in db_uid_map:
                cur.execute("""
                    UPDATE users SET
                        name         = %s,
                        privilege    = %s,
                        user_id_str  = %s,
                        card_no      = %s,
                        is_active    = true,
                        updated_at   = %s
                    WHERE uid = %s
                """, (
                    du.name, du.privilege, str(du.user_id),
                    str(du.card) if du.card else None,
                    datetime.utcnow(), uid
                ))
                print(f"  Updated  uid={uid}  name={du.name}  display_id={du.user_id}")
            else:
                cur.execute("""
                    INSERT INTO users (uid, name, privilege, user_id_str, card_no, is_active, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, true, %s, %s)
                """, (
                    uid, du.name, du.privilege, str(du.user_id),
                    str(du.card) if du.card else None,
                    datetime.utcnow(), datetime.utcnow()
                ))
                print(f"  Inserted uid={uid}  name={du.name}  display_id={du.user_id}")

        db.commit()

        # ── Step 6: Final report ─────────────────────────────────────── #
        print("\n" + "=" * 60)
        print("FINAL DB STATE (active users only)")
        print("=" * 60)
        cur.execute("""
            SELECT uid, name, user_id_str, privilege, is_active
            FROM users
            WHERE is_active = true
            ORDER BY uid
        """)
        rows = cur.fetchall()
        print(f"{'UID':<6} {'Display ID':<12} {'Name':<25} {'Privilege'}")
        print("-" * 55)
        for row in rows:
            print(f"{row['uid']:<6} {row['user_id_str']:<12} {row['name']:<25} {row['privilege']}")
        print("-" * 55)
        print(f"Total active: {len(rows)}")
        print("\nDone. DB now matches device exactly.")

    except Exception as e:
        db.rollback()
        print(f"\nERROR — rolled back: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)
    finally:
        cur.close()
        db.close()


if __name__ == "__main__":
    run()