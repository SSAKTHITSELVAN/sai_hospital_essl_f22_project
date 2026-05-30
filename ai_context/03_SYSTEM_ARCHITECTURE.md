# System Architecture

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │Dashboard │  │ Users    │  │Attendance│  │ Payroll  │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP/REST API
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                            │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    API Layer                                │ │
│  │  /users  /attendance  /payroll  /device  /lop  /export    │ │
│  └───────────────────────┬────────────────────────────────────┘ │
│                          │                                       │
│  ┌───────────────────────┴────────────────────────────────────┐ │
│  │                 Business Logic Layer                        │ │
│  │  ┌──────────────────────┐  ┌──────────────────────┐       │ │
│  │  │ Device Sync Service  │  │Attendance Processor  │       │ │
│  │  │ - Dual device sync   │  │ - Punch pairing      │       │ │
│  │  │ - User sync          │  │ - Status calculation │       │ │
│  │  │ - Log sync           │  │ - Session analysis   │       │ │
│  │  └──────────────────────┘  └──────────────────────┘       │ │
│  └───────────────────────┬────────────────────────────────────┘ │
│                          │                                       │
│  ┌───────────────────────┴────────────────────────────────────┐ │
│  │                   Data Layer (SQLAlchemy)                   │ │
│  │     Users  |  Attendance Logs  |  Processed Attendance     │ │
│  └───────────────────────┬────────────────────────────────────┘ │
└────────────────────────────┼─────────────────────────────────────┘
                             │
                             ▼
                   ┌─────────────────┐
                   │   PostgreSQL    │
                   │    Database     │
                   └─────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    Background Tasks                             │
│  ┌──────────────────────┐  ┌──────────────────────┐           │
│  │  Device Sync Task    │  │    LOP Check Task    │           │
│  │  Every 30 seconds    │  │    Daily at 7 AM     │           │
│  └──────────────────────┘  └──────────────────────┘           │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    Hardware Devices                             │
│  ┌──────────────────────┐  ┌──────────────────────┐           │
│  │  Device 1 (IN)       │  │  Device 2 (OUT)      │           │
│  │  192.168.1.201:4370  │  │  192.168.1.35:4370   │           │
│  │  ESSL F22            │  │  ESSL F22            │           │
│  └──────────────────────┘  └──────────────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Frontend (React)

#### Pages
- **Dashboard:** Overview, today's attendance, device status
- **Users:** Employee list with device registration status
- **Attendance:** Daily records with live timers, IN-1/OUT-1 display
- **Payroll:** Monthly salary calculation, LOP tracking
- **Reports:** Attendance reports, export functionality
- **Login:** Password-based authentication

#### Components
- **Layout:** Sidebar navigation with device status
- **DeviceStatus:** Real-time device connectivity monitor
- **LiveTimer:** Shows elapsed time for ongoing sessions

#### Services
- **api.js:** Axios instance with token interceptor
- **auth.js:** Login/logout, session management

#### Features
- Auto-refresh (30s for today's attendance)
- Live timers for ongoing sessions
- Device registration visualization
- Export to Excel

---

### 2. Backend (FastAPI)

#### API Routes

**Users (`/api/v1/users`)**
- `GET /` - List all users with pagination
- `GET /{uid}` - Get user by UID
- `PUT /{uid}` - Update user
- `DELETE /{uid}` - Soft delete user

**Attendance (`/api/v1/attendance`)**
- `GET /logs` - Raw attendance logs
- `GET /processed` - Processed daily records
- `GET /today` - Today's attendance
- `GET /summary/{uid}` - User attendance summary
- `POST /process` - Trigger attendance processing
- `GET /stats` - Attendance statistics

**Payroll (`/api/v1/payroll`)**
- `GET /monthly` - Monthly payroll calculation
- `GET /user/{uid}` - User-specific payroll

**Device (`/api/v1/device`)**
- `GET /info` - Dual device status
- `POST /sync` - Manual sync trigger

**LOP (`/api/v1/lop`)**
- `GET /` - List LOP records
- `POST /check` - Run LOP check

**Export (`/api/v1/export`)**
- `GET /today-attendance` - Export to Excel
- `GET /monthly-payroll` - Payroll Excel

**Auth (`/api/v1/auth`)**
- `POST /login` - Admin login
- `POST /logout` - Logout

---

### 3. Services Layer

#### DeviceSyncService

**Purpose:** Sync data from both ESSL F22 devices

**Key Methods:**
```python
def full_sync():
    """Complete sync from both devices"""
    1. Connect to both devices
    2. Sync users (merge by name)
    3. Sync attendance logs (tag with device_ip)
    4. Process attendance
    5. Update device status

def sync_users():
    """Sync users from both devices"""
    - Fetch from Device 1 and Device 2
    - Match by name (case-insensitive)
    - Store device_1_uid and device_2_uid
    - Update or insert

def sync_attendance_logs():
    """Sync logs from both devices"""
    - Fetch from both devices
    - Tag with device_ip
    - Match users by device-specific UID
    - Prevent duplicates
```

**Concurrency:**
- Uses thread lock (`_ZK_LOCK`) to prevent simultaneous connections
- Queues sync requests if already running

---

#### AttendanceProcessor

**Purpose:** Process raw logs into daily attendance records

**Key Methods:**
```python
def process_daily_attendance(uid, date):
    """Process one user's attendance for one date"""
    1. Fetch logs in day window
    2. Pair IN/OUT punches
    3. Calculate work hours
    4. Determine status
    5. Save processed record

def process_all_pending():
    """Process all unprocessed attendance"""
    - Finds logs without processed records
    - Processes each user-date combination
    - Returns statistics

def _pair_dual_device(logs, device_1_ip, device_2_ip):
    """Core pairing algorithm"""
    1. Separate by device IP
    2. Deduplicate (2-min window)
    3. Pair chronologically: IN → OUT
    4. Return sessions list

def _determine_status(hours, first_in, last_out, sessions):
    """Calculate attendance status"""
    - Check for complete session
    - Apply hour thresholds
    - Return status enum
```

**Processing Flow:**
```
Raw Logs → Pairing → Hour Calculation → Status → Processed Record
```

---

### 4. Database Layer

#### Models (SQLAlchemy)

**User Model:**
```python
class User(Base):
    id = Integer (PK)
    uid = Integer (unique, indexed)
    device_1_uid = Integer (nullable)
    device_2_uid = Integer (nullable)
    name = String (unique)
    privilege = Integer
    is_active = Boolean
    created_at = DateTime
    updated_at = DateTime
```

**AttendanceLog Model:**
```python
class AttendanceLog(Base):
    id = Integer (PK)
    uid = Integer (FK to User)
    timestamp = DateTime
    punch_type = Integer
    status = Integer
    device_ip = String (tracks which device)
```

**ProcessedAttendance Model:**
```python
class ProcessedAttendance(Base):
    id = Integer (PK)
    uid = Integer (FK to User)
    date = Date
    first_in = DateTime
    last_out = DateTime
    work_duration_hours = Float
    overtime_hours = Float
    status = Enum (PRESENT, HALF_DAY, INCOMPLETE, ABSENT)
    punch_sessions = JSON (list of IN/OUT pairs)
    shift = String (Regular or Break Shift)
    is_finalized = Boolean
```

**Device Model:**
```python
class Device(Base):
    id = Integer (PK)
    device_ip = String (unique)
    device_port = Integer
    last_sync_at = DateTime
    last_sync_status = String
```

#### Relationships
- User ↔ AttendanceLog (one-to-many)
- User ↔ ProcessedAttendance (one-to-many)

---

### 5. Background Tasks

#### Sync Task (Every 30 seconds)
```python
def background_sync():
    while running:
        try:
            sync_service.full_sync()
            time.sleep(30)
        except Exception as e:
            log_error(e)
            time.sleep(30)
```

#### LOP Check Task (Daily at 7 AM)
```python
@scheduler.scheduled_job('cron', hour=7, minute=0)
def daily_lop_check():
    yesterday = date.today() - timedelta(days=1)
    check_and_mark_lop(yesterday)
```

**LOP Check Logic:**
1. Get all active users
2. Check each user's attendance for yesterday
3. If no attendance record → Mark as LOP
4. Create LOP record in processed_attendance

---

## Data Flow

### User Registration Flow
```
1. Admin enrolls finger on Device 1
   ↓
2. Admin enrolls finger on Device 2
   ↓
3. Background sync runs
   ↓
4. DeviceSyncService.sync_users()
   - Fetches from both devices
   - Matches by name
   - Saves device_1_uid and device_2_uid
   ↓
5. User visible in frontend with device status
```

### Attendance Flow (Regular Day)
```
9:00 AM - Employee punches Device 1
   ↓
Device 1 stores log locally
   ↓
Background sync (within 30s)
   ↓
DeviceSyncService.sync_attendance_logs()
   - Fetches log
   - Tags with device_1_ip
   - Saves to attendance_logs table
   ↓
AttendanceProcessor.process_all_pending()
   - Finds new log
   - No OUT yet → Status: INCOMPLETE
   - Saves to processed_attendance
   ↓
Frontend auto-refresh
   - Shows IN-1: 9:00 AM
   - OUT-1: Not Used
   - Status: INCOMPLETE
   - Live timer shows elapsed time

6:00 PM - Employee punches Device 2
   ↓
Device 2 stores log locally
   ↓
Background sync (within 30s)
   ↓
DeviceSyncService.sync_attendance_logs()
   - Fetches OUT log
   - Tags with device_2_ip
   ↓
AttendanceProcessor.process_all_pending()
   - Pairs IN (9:00) with OUT (6:00)
   - Calculates: 9 hours
   - Status: PRESENT
   - Saves updated processed_attendance
   ↓
Frontend auto-refresh
   - Shows IN-1: 9:00 AM, OUT-1: 6:00 PM
   - Status: PRESENT
   - Live timer stops
```

### Payroll Flow
```
Month End
   ↓
Admin views Payroll page
   ↓
Frontend: GET /api/v1/payroll/monthly?month=2026-05
   ↓
Backend calculates:
   - Total days in month
   - Present days
   - Half days (count as 0.5)
   - LOP days
   - Payable days = present + (half_day * 0.5)
   ↓
Returns payroll data
   ↓
Frontend displays with export option
```

---

## Security Architecture

### Authentication
1. **Login:** Password checked against hardcoded admin password
2. **Session:** Token stored in localStorage (30-min expiry)
3. **API Protection:** All routes check token validity
4. **Auto-logout:** Expired sessions redirect to login

### Authorization
- Currently single admin role
- Can be extended to role-based (User, Admin, Super Admin)

### Network Security
- Devices on local network only
- Backend accessible only on LAN
- CORS configured for local origins

---

## Deployment Architecture

### Development
```
Localhost:
- Backend: http://localhost:8000
- Frontend: http://localhost:5173 (Vite dev server)
- Database: PostgreSQL on localhost:5432
```

### Production
```
Server (Local Network):
- Backend: http://192.168.1.X:8000
- Frontend: Served by FastAPI static files
- Database: PostgreSQL on same server
- Devices connect to backend IP
```

---

## Scalability Considerations

### Current Limits
- Single server deployment
- ~500-1000 employees
- 2 devices

### Potential Scaling
- Multiple locations: Separate instances per location
- More devices: Add to device list in config
- Cloud deployment: Use cloud PostgreSQL, deploy on VPS
- Horizontal scaling: Load balancer + multiple backend instances
