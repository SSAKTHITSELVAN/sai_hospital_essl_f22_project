import sqlite3
from datetime import datetime
from zk import ZK, const
import sys

class ESSLFingerprintManager:
    def __init__(self, device_ip, device_port=4370, db_path='fingerprint_data.db', timeout=30):
        """
        Initialize ESSL F22 Fingerprint Manager
        
        Args:
            device_ip: IP address of the F22 device (e.g., '192.168.1.201')
            device_port: Port number (default: 4370)
            db_path: Path to SQLite database file
            timeout: Connection timeout in seconds (default: 30)
        """
        self.device_ip = device_ip
        self.device_port = device_port
        self.db_path = db_path
        self.conn = None
        self.timeout = timeout
        self.zk = ZK(device_ip, port=device_port, timeout=timeout, password=0, 
                     force_udp=False, ommit_ping=True)
        
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database with required tables"""
        self.conn = sqlite3.connect(self.db_path)
        cursor = self.conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                uid INTEGER UNIQUE,
                name TEXT NOT NULL,
                privilege INTEGER DEFAULT 0,
                password TEXT,
                group_id TEXT,
                user_id_str TEXT,
                card_no INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create attendance logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                uid INTEGER,
                user_id INTEGER,
                timestamp TIMESTAMP,
                punch_type INTEGER,
                status INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        # Create fingerprint templates table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fingerprint_templates (
                template_id INTEGER PRIMARY KEY AUTOINCREMENT,
                uid INTEGER,
                fid INTEGER,
                template_data BLOB,
                valid INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (uid) REFERENCES users(uid)
            )
        ''')
        
        self.conn.commit()
        print(f"✓ Database initialized: {self.db_path}")
    
    def connect_device(self):
        """Connect to the ESSL F22 device"""
        try:
            print(f"Attempting to connect to {self.device_ip}:{self.device_port}...")
            print(f"Timeout set to {self.timeout} seconds (device has high latency)")
            self.conn_device = self.zk.connect()
            print(f"✓ Connected to device: {self.device_ip}:{self.device_port}")
            
            # Disable device to prevent interference during data fetch
            self.conn_device.disable_device()
            print("✓ Device disabled for data synchronization")
            return True
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            print("\nTroubleshooting tips:")
            print("  • High network latency detected (up to 973ms)")
            print("  • Try increasing timeout (currently {0}s)".format(self.timeout))
            print("  • Check if device is in TCP/IP mode (not RS232/485)")
            print("  • Verify port 4370 is open in firewall")
            print("  • Try connecting via device's web interface first")
            return False
    
    def disconnect_device(self):
        """Disconnect from the device"""
        if self.conn_device:
            try:
                # Re-enable device before disconnecting
                self.conn_device.enable_device()
                print("✓ Device re-enabled")
            except:
                pass
            self.zk.disconnect()
            print("✓ Device disconnected")
    
    def fetch_users(self):
        """Fetch users from device and store in database"""
        try:
            users = self.conn_device.get_users()
            cursor = self.conn.cursor()
            
            print(f"\n{'='*80}")
            print(f"FETCHING USERS FROM DEVICE")
            print(f"{'='*80}")
            
            for user in users:
                cursor.execute('''
                    INSERT OR REPLACE INTO users 
                    (uid, name, privilege, password, group_id, user_id_str, card_no, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user.uid,
                    user.name,
                    user.privilege,
                    user.password,
                    user.group_id,
                    user.user_id,
                    user.card,
                    datetime.now()
                ))
                
                print(f"UID: {user.uid:5d} | Name: {user.name:20s} | Privilege: {user.privilege} | Card: {user.card}")
            
            self.conn.commit()
            print(f"\n✓ {len(users)} users fetched and stored in database")
            return len(users)
            
        except Exception as e:
            print(f"✗ Error fetching users: {e}")
            return 0
    
    def fetch_attendance_logs(self):
        """Fetch attendance logs from device and store in database"""
        try:
            logs = self.conn_device.get_attendance()
            cursor = self.conn.cursor()
            
            print(f"\n{'='*80}")
            print(f"FETCHING ATTENDANCE LOGS FROM DEVICE")
            print(f"{'='*80}")
            
            for log in logs:
                try:
                    # Convert timestamp to string if it's not already
                    timestamp_str = str(log.timestamp) if log.timestamp else None
                    
                    cursor.execute('''
                        INSERT OR IGNORE INTO attendance_logs 
                        (uid, user_id, timestamp, punch_type, status)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        log.user_id,
                        log.user_id,
                        timestamp_str,
                        log.punch,
                        log.status
                    ))
                    
                    # Safe printing with string formatting
                    uid_str = str(log.user_id).rjust(5)
                    print(f"UID: {uid_str} | Time: {timestamp_str} | Punch: {log.punch} | Status: {log.status}")
                except Exception as log_error:
                    print(f"  ⚠ Skipped malformed log entry: {log_error}")
                    continue
            
            self.conn.commit()
            print(f"\n✓ {len(logs)} attendance logs fetched and stored in database")
            return len(logs)
            
        except Exception as e:
            print(f"✗ Error fetching logs: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    def fetch_fingerprints(self):
        """Fetch fingerprint templates from device and store in database"""
        try:
            templates = self.conn_device.get_templates()
            cursor = self.conn.cursor()
            
            print(f"\n{'='*80}")
            print(f"FETCHING FINGERPRINT TEMPLATES FROM DEVICE")
            print(f"{'='*80}")
            
            for template in templates:
                cursor.execute('''
                    INSERT OR REPLACE INTO fingerprint_templates 
                    (uid, fid, template_data, valid)
                    VALUES (?, ?, ?, ?)
                ''', (
                    template.uid,
                    template.fid,
                    template.template,
                    template.valid
                ))
                
                print(f"UID: {template.uid:5d} | FID: {template.fid} | Size: {len(template.template)} bytes | Valid: {template.valid}")
            
            self.conn.commit()
            print(f"\n✓ {len(templates)} fingerprint templates fetched and stored")
            return len(templates)
            
        except Exception as e:
            print(f"✗ Error fetching fingerprints: {e}")
            return 0
    
    def print_all_users(self):
        """Print all users from database"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users ORDER BY uid')
        users = cursor.fetchall()
        
        print(f"\n{'='*80}")
        print(f"ALL USERS IN DATABASE (Total: {len(users)})")
        print(f"{'='*80}")
        print(f"{'UID':<6} {'Name':<20} {'Privilege':<10} {'Card No':<15} {'Created':<20}")
        print(f"{'-'*80}")
        
        for user in users:
            print(f"{user[1]:<6} {user[2]:<20} {user[3]:<10} {user[7] or 'N/A':<15} {user[8]:<20}")
    
    def print_all_logs(self):
        """Print all attendance logs from database"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT al.*, u.name 
            FROM attendance_logs al
            LEFT JOIN users u ON al.uid = u.uid
            ORDER BY al.timestamp DESC
        ''')
        logs = cursor.fetchall()
        
        print(f"\n{'='*80}")
        print(f"ALL ATTENDANCE LOGS IN DATABASE (Total: {len(logs)})")
        print(f"{'='*80}")
        print(f"{'UID':<6} {'Name':<20} {'Timestamp':<20} {'Type':<6} {'Status':<8}")
        print(f"{'-'*80}")
        
        for log in logs:
            name = log[7] if log[7] else "Unknown"
            print(f"{log[1]:<6} {name:<20} {log[3]:<20} {log[4]:<6} {log[5]:<8}")
    
    def print_device_info(self):
        """Print device information"""
        try:
            print(f"\n{'='*80}")
            print(f"DEVICE INFORMATION")
            print(f"{'='*80}")
            print(f"Device IP: {self.device_ip}:{self.device_port}")
            print(f"Firmware Version: {self.conn_device.get_firmware_version()}")
            print(f"Serial Number: {self.conn_device.get_serialnumber()}")
            print(f"Platform: {self.conn_device.get_platform()}")
            print(f"Device Name: {self.conn_device.get_device_name()}")
            print(f"MAC Address: {self.conn_device.get_mac()}")
        except Exception as e:
            print(f"✗ Error getting device info: {e}")
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            print("\n✓ Database connection closed")


def main():
    """Main function to run the ESSL Fingerprint Manager"""
    
    # Configuration
    DEVICE_IP = '192.168.1.201'  # Your F22 device IP
    DEVICE_PORT = 4370
    DATABASE_PATH = 'essl_fingerprint.db'
    TIMEOUT = 30  # Increased timeout due to high latency
    
    print(f"\n{'#'*80}")
    print(f"{'ESSL F22 FINGERPRINT SENSOR DATA MANAGER':^80}")
    print(f"{'#'*80}\n")
    
    # Initialize manager
    manager = ESSLFingerprintManager(DEVICE_IP, DEVICE_PORT, DATABASE_PATH, TIMEOUT)
    
    try:
        # Connect to device
        if not manager.connect_device():
            print("\n✗ Failed to connect to device. Please check:")
            print("  1. Device IP address is correct")
            print("  2. Device is powered on and connected to network")
            print("  3. Firewall is not blocking the connection")
            sys.exit(1)
        
        # Print device information
        manager.print_device_info()
        
        # Fetch all data from device
        manager.fetch_users()
        manager.fetch_attendance_logs()
        manager.fetch_fingerprints()
        
        # Print all data from database
        manager.print_all_users()
        manager.print_all_logs()
        
        # Disconnect from device
        manager.disconnect_device()
        
    except KeyboardInterrupt:
        print("\n\n✗ Operation cancelled by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")
    finally:
        manager.close()


if __name__ == "__main__":
    main()

#================================================

# import psycopg2

# # Replace these with your actual details
# DB_HOST = "essldb.c8vick2gctcb.us-east-1.rds.amazonaws.com"
# DB_PORT = "5432"
# DB_NAME = "postgres"
# DB_USER = "postgres"
# DB_PASS = "essl1234"

# try:
#     conn = psycopg2.connect(
#         host=DB_HOST,
#         port=DB_PORT,
#         database=DB_NAME,
#         user=DB_USER,
#         password=DB_PASS
#     )
#     print("✅ Connected successfully to AWS RDS PostgreSQL!")

#     cur = conn.cursor()
#     cur.execute("SELECT version();")
#     version = cur.fetchone()
#     print("PostgreSQL version:", version)

#     cur.close()
#     conn.close()

# except Exception as e:
#     print("❌ Connection failed:", e)