# Debug link (cluad) -> https://claude.ai/share/09df32d0-9f83-4014-b379-fa6938bb4791

# ESSL F22 Fingerprint Attendance System

A comprehensive FastAPI-based system for managing ESSL F22 fingerprint attendance devices with automatic synchronization, shift detection, and attendance processing.

## 🌟 Features

- **Automatic Device Synchronization**: Background tasks sync data every 5 minutes
- **Intelligent Shift Detection**: Automatically detects shifts (A/B/C/G) from punch timestamps
- **Smart Attendance Processing**: Handles edge cases (missing punches, multiple punches, etc.)
- **RESTful API**: Clean, standardized API responses
- **PostgreSQL Database**: Robust data storage with AWS RDS support
- **Device Webhook Support**: Receives real-time data from F22 device
- **Comprehensive Reporting**: Attendance summaries and analytics

## 📁 Project Structure

```
essl-attendance-system/
│
├── app/
│   ├── main.py                      # FastAPI application
│   ├── config.py                    # Configuration
│   │
│   ├── core/
│   │   ├── database.py              # Database setup
│   │   ├── response.py              # Standard responses
│   │   └── exceptions.py
│   │
│   ├── models/
│   │   ├── user.py                  # User model
│   │   ├── attendance.py            # Attendance models
│   │   └── device.py                # Device model
│   │
│   ├── services/
│   │   ├── device_sync.py           # Device sync service
│   │   ├── attendance_processor.py  # Attendance processing
│   │   └── shift_detector.py        # Shift detection
│   │
│   ├── api/routes/
│   │   ├── users.py                 # User endpoints
│   │   ├── attendance.py            # Attendance endpoints
│   │   ├── device.py                # Device endpoints
│   │   └── iclock.py                # Device webhook
│   │
│   └── background/
│       └── tasks.py                 # Background jobs
│
├── .env                             # Environment variables
├── requirements.txt                 # Dependencies
└── README.md
```

## 🚀 Quick Start

### 1. Installation

```bash
# Clone or create project directory
mkdir essl-attendance-system
cd essl-attendance-system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create `.env` file:

```env
# Database Configuration
DB_HOST=essldb.c8vick2gctcb.us-east-1.rds.amazonaws.com
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASS=essl1234

# Device Configuration
DEVICE_IP=10.215.111.231
DEVICE_PORT=4370
DEVICE_TIMEOUT=30

# Application Configuration
APP_HOST=0.0.0.0
APP_PORT=8000
SYNC_INTERVAL_MINUTES=5

# Shift Timings
SHIFT_A_START=07:00
SHIFT_A_END=15:00
SHIFT_B_START=15:00
SHIFT_B_END=23:00
SHIFT_C_START=23:00
SHIFT_C_END=07:00
SHIFT_G_START=09:00
SHIFT_G_END=17:00

# Grace periods
LATE_GRACE_MINUTES=15
EARLY_LEAVE_GRACE_MINUTES=15
```

### 3. Run Application

```bash
# Run with uvicorn
python app/main.py

# Or with uvicorn directly
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Configure F22 Device

Configure your F22 device to push data to:

```
http://YOUR_LOCAL_IP:8000/iclock/cdata
```

**Steps:**
1. Access device web interface
2. Go to Communication Settings
3. Set Push URL to your server address
4. Enable auto-push

## 📡 API Endpoints

### User Management

```bash
# Get all users
GET /api/v1/users?skip=0&limit=100

# Get user by UID
GET /api/v1/users/{uid}
```

### Attendance

```bash
# Get raw attendance logs
GET /api/v1/attendance/logs?uid=1&start_date=2024-01-01&end_date=2024-01-31

# Get processed attendance
GET /api/v1/attendance/processed?uid=1&start_date=2024-01-01&end_date=2024-01-31

# Get attendance summary
GET /api/v1/attendance/summary/{uid}?start_date=2024-01-01&end_date=2024-01-31

# Manually process attendance
POST /api/v1/attendance/process?uid=1&target_date=2024-01-15
```

### Device Management

```bash
# Trigger manual sync
POST /api/v1/device/sync

# Get device info
GET /api/v1/device/info
```

### System

```bash
# Health check
GET /health

# API documentation
GET /docs
```

## 🔄 How It Works

### 1. Data Flow

```
F22 Device → Webhook → Raw Logs → Processing → Processed Attendance
     ↓                                              ↓
Background Sync (Every 5 min)            Shift Detection & Analytics
```

### 2. Shift Detection Logic

The system automatically detects shifts based on punch time:

- **Shift A (Morning)**: 07:00 - 15:00
- **Shift B (Afternoon)**: 15:00 - 23:00
- **Shift C (Night)**: 23:00 - 07:00
- **Shift G (General)**: 09:00 - 17:00

### 3. Attendance Processing

For each day, the system:
1. Groups all punches by user and date
2. Detects shift from first punch
3. Finds first IN and last OUT
4. Calculates work duration
5. Determines status (PRESENT, LATE, EARLY_LEAVE, INCOMPLETE, etc.)
6. Handles edge cases:
   - **Missing OUT**: Marked as INCOMPLETE
   - **Missing IN**: Marked as INCOMPLETE
   - **Multiple punches**: Uses first IN and last OUT
   - **Night shift**: Handles midnight crossing correctly

### 4. Status Types

- **PRESENT**: Normal attendance
- **LATE**: Checked in after grace period
- **EARLY_LEAVE**: Left before shift end
- **INCOMPLETE**: Missing IN or OUT punch
- **HALF_DAY**: Worked less than half shift hours
- **ABSENT**: No punches (rare, system doesn't create records)

## 📊 Database Schema

### Users Table
```sql
- id (PK)
- uid (Unique, Device UID)
- name
- privilege
- card_no
- is_active
- created_at, updated_at
```

### Attendance Logs Table (Raw)
```sql
- id (PK)
- uid (FK)
- timestamp
- punch_type (0=IN, 1=OUT)
- status
- device_id
- created_at
```

### Processed Attendance Table
```sql
- id (PK)
- uid (FK)
- date
- shift (A/B/C/G)
- first_in
- last_out
- work_duration_hours
- status (PRESENT/LATE/etc)
- is_late, late_by_minutes
- is_early_leave, early_leave_by_minutes
- total_punches
- remarks
- created_at, updated_at
```

## 🔧 Configuration Options

### Shift Timings
Customize shift hours in `.env`:
```env
SHIFT_A_START=07:00
SHIFT_A_END=15:00
```

### Grace Periods
```env
LATE_GRACE_MINUTES=15        # Allow 15 min late without penalty
EARLY_LEAVE_GRACE_MINUTES=15 # Allow 15 min early leave
```

### Sync Interval
```env
SYNC_INTERVAL_MINUTES=5      # Background sync every 5 minutes
```

## 🎯 API Response Format

All endpoints return standardized responses:

### Success Response
```json
{
  "status": "success",
  "message": "Operation completed successfully",
  "data": { ... },
  "error": null
}
```

### Error Response
```json
{
  "status": "error",
  "message": "Operation failed",
  "data": null,
  "error": {
    "type": "ValidationError",
    "details": "..."
  }
}
```

## 🛠️ Development

### Add New Endpoints

1. Create route file in `app/api/routes/`
2. Define router: `router = APIRouter(prefix="/endpoint", tags=["Tag"])`
3. Add endpoints with proper response format
4. Include router in `main.py`

### Add New Services

1. Create service file in `app/services/`
2. Implement business logic
3. Use service in route handlers

### Database Migrations

```bash
# Install Alembic
pip install alembic

# Initialize
alembic init alembic

# Create migration
alembic revision --autogenerate -m "description"

# Apply migration
alembic upgrade head
```

## 🚨 Troubleshooting

### Device Connection Issues

1. **Check network**: Ping device IP
2. **Verify port**: Ensure 4370 is open
3. **Increase timeout**: Set `DEVICE_TIMEOUT=60` in `.env`
4. **Check device mode**: Must be in TCP/IP mode

### Background Sync Not Running

1. Check logs for errors
2. Verify device is reachable
3. Check database connection
4. Restart application

### Missing Attendance Records

1. Check raw logs: `GET /api/v1/attendance/logs`
2. Manually trigger processing: `POST /api/v1/attendance/process`
3. Verify shift timings in configuration

## 📈 Performance Tips

- Use pagination for large datasets
- Index frequently queried columns
- Monitor database connection pool
- Adjust sync interval based on needs
- Use caching for static data

## 🔒 Security Recommendations

- Use strong database passwords
- Enable HTTPS in production
- Restrict CORS origins
- Implement authentication/authorization
- Use environment variables for secrets
- Regular security updates

## 📝 License

MIT License

## 🤝 Support

For issues and questions:
- Check API documentation: `/docs`
- Review logs
- Check database records
- Verify device configuration

---

**Made with ❤️ for efficient attendance management**

=========================================
Curl

curl -X 'GET' \
  'http://localhost:8000/api/v1/device/info' \
  -H 'accept: application/json'
Request URL
http://localhost:8000/api/v1/device/info
Server response
Code	Details
200	
Response body
Download
{
  "status": "success",
  "message": "Device information retrieved",
  "data": {
    "ip": "10.215.111.231",
    "port": 4370,
    "firmware_version": "Ver 6.60 Apr 13 2022",
    "serial_number": "JJA1251201371",
    "platform": "ZLM60_TFT",
    "device_name": "x 2008",
    "mac_address": "00:17:61:10:a6:42"
  },
  "error": null
}
=============
Curl

curl -X 'POST' \
  'http://localhost:8000/api/v1/device/sync' \
  -H 'accept: application/json' \
  -d ''
Request URL
http://localhost:8000/api/v1/device/sync
Server response
Code	Details
200	
Response body
Download
{
  "status": "success",
  "message": "Device synchronization completed",
  "data": {
    "status": "success",
    "timestamp": "2025-11-08T02:12:25.174891",
    "users": {
      "total": 8,
      "added": 1,
      "updated": 7
    },
    "logs": {
      "total": 46,
      "new": 1,
      "duplicates": 45,
      "errors": 0
    },
    "processed_attendance": {
      "processed": 19,
      "errors": 0,
      "total": 19
    },
    "device_info": {
      "ip": "10.215.111.231",
      "port": 4370,
      "firmware_version": "Ver 6.60 Apr 13 2022",
      "serial_number": "JJA1251201371",
      "platform": "ZLM60_TFT",
      "device_name": "x 2008",
      "mac_address": "00:17:61:10:a6:42"
    }
  },
  "error": null
}
=========