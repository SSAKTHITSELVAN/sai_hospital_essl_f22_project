"""
query_device_users.py
---------------------
Standalone script to retrieve and display all users from ESSL F22 device.
No database interaction — read-only query directly from device.

Usage:
    python3 query_device_users.py
    python3 query_device_users.py --ip 192.168.1.100 --port 4370
    python3 query_device_users.py --uid 2          # filter specific uid
    python3 query_device_users.py --export users.csv
"""

import argparse
import sys
import csv
from zk import ZK

# ── Config (change these or pass via CLI args) ─────────────────────────── #
DEFAULT_IP      = "192.168.1.201"   # your device IP
DEFAULT_PORT    = 4370
DEFAULT_TIMEOUT = 30
# ────────────────────────────────────────────────────────────────────────── #


def get_users(ip, port, timeout, filter_uid=None):
    zk   = ZK(ip, port=port, timeout=timeout, password=0, force_udp=False, ommit_ping=True)
    conn = None
    try:
        print(f"Connecting to device {ip}:{port} ...")
        conn = zk.connect()
        conn.disable_device()
        print("Connected.\n")

        users = conn.get_users()

        # Filter by uid if requested
        if filter_uid is not None:
            users = [u for u in users if u.uid == filter_uid]

        return users

    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        if conn:
            conn.enable_device()
            zk.disconnect()
            print("\nDevice disconnected.")


def print_table(users):
    if not users:
        print("No users found.")
        return

    # Header
    print(f"{'UID':<6} {'User ID (display)':<20} {'Name':<25} {'Privilege':<12} {'Card':<15}")
    print("-" * 80)

    for u in sorted(users, key=lambda x: x.uid):
        card = str(u.card) if u.card else "-"
        print(f"{u.uid:<6} {str(u.user_id):<20} {u.name:<25} {u.privilege:<12} {card:<15}")

    print("-" * 80)
    print(f"Total: {len(users)} users")


def export_csv(users, filepath):
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["uid", "user_id_display", "name", "privilege", "card"])
        for u in sorted(users, key=lambda x: x.uid):
            writer.writerow([u.uid, u.user_id, u.name, u.privilege, u.card or ""])
    print(f"Exported {len(users)} users to {filepath}")


def main():
    parser = argparse.ArgumentParser(description="Query users from ESSL F22 device")
    parser.add_argument("--ip",      default=DEFAULT_IP,      help="Device IP address")
    parser.add_argument("--port",    default=DEFAULT_PORT,    type=int)
    parser.add_argument("--timeout", default=DEFAULT_TIMEOUT, type=int)
    parser.add_argument("--uid",     default=None,            type=int, help="Filter by specific UID slot")
    parser.add_argument("--export",  default=None,            help="Export to CSV file path")
    args = parser.parse_args()

    users = get_users(args.ip, args.port, args.timeout, filter_uid=args.uid)
    print_table(users)

    if args.export:
        export_csv(users, args.export)


if __name__ == "__main__":
    main()