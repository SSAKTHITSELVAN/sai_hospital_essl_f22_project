# diag_1_device_raw.py
# Run: python diag_1_device_raw.py
# Shows exactly what the ESSL F22 device is sending — punch types, times, all raw data.
# Run with device CONNECTED (same LAN).

import sys
sys.path.insert(0, '.')

DEVICE_IP   = "192.168.1.201"   # ← change to your device IP
DEVICE_PORT = 4370

PUNCH_TYPE_NAMES = {
    0: "CHECKIN",
    1: "CHECKOUT",
    2: "BREAK_OUT",
    3: "BREAK_IN",
    4: "OVERTIME_IN",
    5: "OVERTIME_OUT",
    255: "UNKNOWN",
}

print(f"\n{'='*70}")
print(f"ESSL F22 DEVICE DIAGNOSTICS — Direct Connection")
print(f"Device: {DEVICE_IP}:{DEVICE_PORT}")
print(f"{'='*70}")

try:
    from zk import ZK
except ImportError:
    print("❌ pyzk not installed. Run: pip install pyzk")
    sys.exit(1)

zk   = ZK(DEVICE_IP, port=DEVICE_PORT, timeout=30, password=0, force_udp=False, ommit_ping=True)
conn = None

try:
    print("\n→ Connecting to device...")
    conn = zk.connect()
    print("✅ Connected")

    # ── Device info ──────────────────────────────────────────────────────── #
    print(f"\n{'─'*70}")
    print("DEVICE INFO:")
    print(f"{'─'*70}")
    try:
        print(f"  Firmware:     {conn.get_firmware_version()}")
        print(f"  Serial:       {conn.get_serialnumber()}")
        print(f"  Platform:     {conn.get_platform()}")
        print(f"  Device Name:  {conn.get_device_name()}")
        print(f"  MAC:          {conn.get_mac()}")
    except Exception as e:
        print(f"  (Some info unavailable: {e})")

    # ── Users ────────────────────────────────────────────────────────────── #
    print(f"\n{'─'*70}")
    print("USERS ON DEVICE:")
    print(f"{'─'*70}")
    conn.disable_device()
    users = conn.get_users()
    print(f"  Total users: {len(users)}")
    print(f"  {'slot_uid':<10} {'user_id':<12} {'name':<25} {'privilege'}")
    print(f"  {'-'*60}")
    for u in users:
        print(f"  {u.uid:<10} {str(u.user_id):<12} {u.name:<25} {u.privilege}")

    # ── Raw attendance logs ───────────────────────────────────────────────── #
    print(f"\n{'─'*70}")
    print("RAW ATTENDANCE LOGS FROM DEVICE:")
    print(f"{'─'*70}")
    logs = conn.get_attendance()
    print(f"  Total logs: {len(logs)}")
    print()
    print(f"  {'#':<5} {'user_id':<10} {'timestamp':<22} {'punch':<6} {'punch_name':<16} {'status'}")
    print(f"  {'-'*70}")
    for i, log in enumerate(sorted(logs, key=lambda l: l.timestamp), 1):
        punch_name = PUNCH_TYPE_NAMES.get(log.punch, f"UNKNOWN({log.punch})")
        print(
            f"  {i:<5} {str(log.user_id):<10} {str(log.timestamp):<22} "
            f"{log.punch:<6} {punch_name:<16} {log.status}"
        )

    # ── Punch type distribution ───────────────────────────────────────────── #
    print(f"\n{'─'*70}")
    print("PUNCH TYPE DISTRIBUTION (what types does this device send?):")
    print(f"{'─'*70}")
    from collections import Counter
    type_counts = Counter(log.punch for log in logs)
    all_zero = all(log.punch == 0 for log in logs)
    for ptype, count in sorted(type_counts.items()):
        name = PUNCH_TYPE_NAMES.get(ptype, f"UNKNOWN({ptype})")
        print(f"  Type {ptype} ({name}): {count} punches")

    print(f"\n  → Mode: {'Mode B (all type 0 — ordinal only)' if all_zero else 'Mode A (real punch types ✓)'}")

    # ── Per-user summary ──────────────────────────────────────────────────── #
    print(f"\n{'─'*70}")
    print("PUNCHES PER USER (last 7 days):")
    print(f"{'─'*70}")
    from datetime import datetime, timedelta
    cutoff = datetime.now() - timedelta(days=7)
    recent = [l for l in logs if l.timestamp >= cutoff]
    from collections import defaultdict
    user_logs = defaultdict(list)
    for l in recent:
        user_logs[str(l.user_id)].append(l)

    user_map = {str(u.user_id): u.name for u in users}
    for uid_str, ulogs in sorted(user_logs.items()):
        name = user_map.get(uid_str, "Unknown")
        print(f"\n  User {uid_str} ({name}) — {len(ulogs)} punches:")
        for l in sorted(ulogs, key=lambda x: x.timestamp):
            pname = PUNCH_TYPE_NAMES.get(l.punch, f"?({l.punch})")
            print(f"    {l.timestamp.strftime('%Y-%m-%d %H:%M')}  type={l.punch} ({pname})")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback; traceback.print_exc()

finally:
    if conn:
        try:
            conn.enable_device()
            zk.disconnect()
            print(f"\n✅ Device disconnected")
        except:
            pass

print(f"\n{'='*70}")
print("Copy this full output and share for analysis.")
print(f"{'='*70}\n")