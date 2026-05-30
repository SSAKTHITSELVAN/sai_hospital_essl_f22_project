# MS Softwares - Dual Device Attendance System Overview

**Complete system documentation for administrators**

---

## 📖 Table of Contents

1. [System Architecture](#system-architecture)
2. [How It Works](#how-it-works)
3. [Key Features](#key-features)
4. [Configuration](#configuration)
5. [User Guide](#user-guide)
6. [Admin Guide](#admin-guide)
7. [API Reference](#api-reference)
8. [File Structure](#file-structure)

---

## 🏗️ System Architecture

### **Overview**

```
┌─────────────────┐         ┌─────────────────┐
│   Device 1      │         │   Device 2      │
│  (Entry/IN)     │         │  (Exit/OUT)     │
│ 192.168.1.201   │         │ 192.168.1.35    │
└────────┬────────┘         └────────┬────────┘
         │                           │
         │   Background Sync (5min)  │
         │                           │
         └──────────┬────────────────┘
                    │
         ┌──────────▼──────────┐
         │   Backend Server    │
         │   FastAPI + Python  │
         │   Port 8000         │
         └──────────┬──────────┘
                    │
         ┌──────────▼──────────┐
         │   PostgreSQL DB     │
         │   Port 5432         │
         └──────────┬──────────┘
                    │
         ┌──────────▼──────────┐
         │   Frontend UI       │
         │   React + Vite      │
         │   Port 5174         │
         └─────────────────────┘
```

### **Technology Stack**

**Backend:**
- FastAPI (REST API)
- SQLAlchemy (ORM)
- PostgreSQL (Database)
- pyzk (ESSL communication)
- openpyxl (Excel export)
- APScheduler (Background tasks)

**Frontend:**
- React 19
- TailwindCSS
- Axios
- React Router
- Lucide Icons

---

## ⚙️ How It Works

### **1. User Registration**

Users must be registered on **BOTH** devices with the **SAME NAME**:

```
Device 1:                    Device 2:
┌────────────────┐          ┌────────────────┐
│ Name: John     │          │ Name: John     │
│ UID:  5        │  ✅      │ UID:  21       │
│ Type: IN       │          │ Type: OUT      │
└────────────────┘          └────────────────┘

System matches by NAME → Creates ONE user in DB
```

### **2. Punch Flow**

```
Morning Entry:
Employee → Device 1 → Punch (09:00 AM)
         ↓
System syncs → Stores as IN punch with device_ip=192.168.1.201
         ↓
UI shows: IN time 09:00 AM

Evening Exit:
Employee → Device 2 → Punch (06:00 PM)
         ↓
System syncs → Stores as OUT punch with device_ip=192.168.1.35
         ↓
UI shows: IN 09:00 AM → OUT 06:00 PM (9 hours)
```

### **3. Session Detection**

**Regular Shift:**
```
1 IN + 1 OUT = 1 Session
Example: IN 09:00 AM → OUT 06:00 PM
Result: 9 hours, Status: PRESENT
```

**Break Shift:**
```
2 INs + 2 OUTs = 2 Sessions
Session 1: IN 08:00 AM → OUT 12:00 PM (4 hours)
Session 2: IN 01:00 PM → OUT 06:00 PM (5 hours)
Result: 9 hours, Status: PRESENT
```

### **4. Status Logic**

```python
if work_hours >= 9.0:
    status = "PRESENT"
elif work_hours >= 4.5:
    status = "HALF_DAY"
else:
    status = "INCOMPLETE"
```

---

## 🎯 Key Features

### **1. Dual Device System**
- Device 1 = Entry (IN punches only)
- Device 2 = Exit (OUT punches only)
- Name-based user matching
- Different UIDs supported

### **2. Auto-Detection**
- Regular vs Break Shift (automatic)
- Latest punch wins (handles duplicates)
- Chronological pairing
- Midnight crossing support

### **3. Real-Time Monitoring**
- Live device status
- Auto-sync every 5 minutes
- Manual sync option
- Status indicators

### **4. Comprehensive Reports**
- Daily attendance
- Date range payroll
- Per-user detailed reports
- MS Excel export (.xlsx)

### **5. Enterprise UI**
- Professional design
- Mobile responsive
- Dual device status in header
- Search and filters

---

## 🔧 Configuration

### **Environment Variables (.env)**

```env
# Device Configuration
DEVICE_1_IP=192.168.1.201      # Entry device IP
DEVICE_1_PORT=4370              # Device port
DEVICE_2_IP=192.168.1.35        # Exit device IP
DEVICE_2_PORT=4370              # Device port

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=essl_v2
DB_USER=postgres
DB_PASS=your_password

# Application
APP_HOST=0.0.0.0
APP_PORT=8000
SYNC_INTERVAL_MINUTES=5         # Background sync interval

# Attendance Rules
DAY_START_TIME=08:00            # When new day starts
PRESENT_HOURS=9.0               # Full day threshold
HALF_DAY_HOURS=4.5              # Half day threshold
```

### **Important Settings**

**SYNC_INTERVAL_MINUTES:**
- `1` = Fast (1 minute delay)
- `5` = Default (5 minute delay)
- `10` = Slow (10 minute delay)

**DAY_START_TIME:**
- For day shift: `08:00` or `09:00`
- For night shift: Set AFTER night shift ends
- Example: Night shift ends 7 AM → Use `08:00`

**Work Hours:**
- `PRESENT_HOURS`: Full day minimum (default: 9.0)
- `HALF_DAY_HOURS`: Half day minimum (default: 4.5)

---

## 👤 User Guide

### **For Employees**

**Daily Routine:**
1. **Morning/Entry**: Punch on **Device 1** (Entry device)
2. **Evening/Exit**: Punch on **Device 2** (Exit device)

**Break Shift:**
1. **Morning Entry**: Punch on Device 1
2. **Lunch Break OUT**: Punch on Device 2
3. **After Lunch IN**: Punch on Device 1
4. **Evening Exit**: Punch on Device 2

**Result:** System automatically detects 2 sessions.

---

## 👨‍💼 Admin Guide

### **Daily Tasks**

**Morning:**
- Check Dashboard for device status
- Verify both devices online
- Review today's attendance

**During Day:**
- Monitor real-time attendance
- Check for incomplete records
- Handle employee queries

**End of Day:**
- Export daily attendance
- Review incomplete statuses
- Check sync status

### **Monthly Tasks**

**Payroll Generation:**
1. Go to Payroll page
2. Select date range (e.g., 1st to 30th)
3. Review summary
4. Export to Excel
5. Share with accounts team

### **User Management**

**Adding New Employee:**
1. Register on Device 1 with name
2. Register on Device 2 with **SAME NAME**
3. System auto-creates user record
4. Verify in Employees page

**Removing Employee:**
1. Remove from both devices
2. System auto-deactivates on next sync
3. Historical data preserved

---

## 📡 API Reference

### **Device Endpoints**

```
POST /api/v1/device/sync
- Manually trigger sync from both devices
- Returns: sync summary

GET /api/v1/device/info
- Get status of both devices
- Returns: device_1 and device_2 info
```

### **Attendance Endpoints**

```
GET /api/v1/attendance/today
- Get today's attendance
- Returns: all records for current date

GET /api/v1/attendance/processed?start_date=X&end_date=Y
- Get processed attendance for date range
- Returns: attendance records with sessions

GET /api/v1/attendance/logs?uid=X&start_date=Y&end_date=Z
- Get raw punch logs
- Returns: all punches with device_ip
```

### **Export Endpoints**

```
GET /api/v1/export/today-attendance
- Download today's attendance Excel

GET /api/v1/export/payroll-report?start_date=X&end_date=Y
- Download payroll report Excel

GET /api/v1/export/detailed-attendance/{uid}?start_date=X&end_date=Y
- Download detailed user report Excel
```

### **User Endpoints**

```
GET /api/v1/users
- Get all users
- Returns: user list

GET /api/v1/users/{uid}
- Get specific user
- Returns: user details
```

---

## 📁 File Structure

```
project/
├── app/
│   ├── main.py                          # FastAPI app
│   ├── config.py                        # Configuration
│   │
│   ├── core/
│   │   ├── database.py                  # DB connection
│   │   └── response.py                  # API responses
│   │
│   ├── models/
│   │   ├── user.py                      # User model
│   │   ├── attendance.py                # Attendance models
│   │   └── device.py                    # Device model
│   │
│   ├── services/
│   │   ├── device_sync.py               # Dual device sync ⭐
│   │   ├── attendance_processor.py      # Attendance logic ⭐
│   │   └── excel_export.py              # Excel exports
│   │
│   └── api/routes/
│       ├── users.py                     # User endpoints
│       ├── attendance.py                # Attendance endpoints
│       ├── device.py                    # Device endpoints
│       ├── payroll.py                   # Payroll endpoints
│       └── export.py                    # Export endpoints ⭐
│
├── frontend/src/
│   ├── pages/
│   │   ├── Dashboard.jsx                # Main dashboard ⭐
│   │   ├── Users.jsx                    # Employee management ⭐
│   │   ├── Attendance.jsx               # Daily attendance ⭐
│   │   └── Payroll.jsx                  # Payroll reports ⭐
│   │
│   └── components/
│       ├── Layout.jsx                   # App layout ⭐
│       └── DeviceStatus.jsx             # Device status ⭐
│
├── migrations/
│   └── add_device_ip_column.sql         # DB migration ⭐
│
├── .env                                  # Configuration ⭐
├── run.py                                # Start backend
├── test_dual_device_sync.py             # Test script ⭐
│
├── README.md                             # Main documentation ⭐
├── QUICK_START.md                        # Quick start guide ⭐
├── TROUBLESHOOTING.md                    # Problem solving ⭐
└── SYSTEM_OVERVIEW.md                    # This file ⭐
```

**⭐ = Modified/Created for dual device system**

---

## 🔐 Security Notes

1. **Database**: Use strong password for PostgreSQL
2. **Network**: Keep devices on secure network
3. **Access**: Implement user authentication (login system included)
4. **Backup**: Regular database backups recommended
5. **Updates**: Keep system updated

---

## 📊 Database Schema

### **users**
```sql
- id: Primary key
- uid: Device UID (from Device 1)
- name: Employee name (used for matching)
- privilege: User level
- is_active: Active status
- created_at: Registration date
```

### **attendance_logs**
```sql
- id: Primary key
- uid: User UID (foreign key)
- timestamp: Punch time
- punch_type: Punch mode (0-5)
- device_ip: Source device IP ⭐ KEY FIELD
- created_at: Record creation time
```

### **processed_attendance**
```sql
- id: Primary key
- uid: User UID (foreign key)
- date: Work date
- punch_sessions: JSON array of sessions ⭐
- shift: "Regular" or "Break Shift"
- first_in: First IN time
- last_out: Last OUT time
- work_duration_hours: Total hours
- status: PRESENT/HALF_DAY/INCOMPLETE
```

---

## 📈 Performance Tips

1. **Sync Interval**: Lower = more real-time but more load
2. **Database**: Add indexes on frequently queried fields
3. **Backup**: Schedule during off-peak hours
4. **Logs**: Rotate old attendance logs (>6 months)
5. **Network**: Use wired connection for devices

---

## 🎯 Best Practices

1. **User Names**: Keep consistent across devices
2. **Device Labels**: Clearly mark Device 1 (IN) and Device 2 (OUT)
3. **Training**: Educate employees on correct punch flow
4. **Monitoring**: Check device status daily
5. **Reports**: Generate monthly reports for records
6. **Backup**: Weekly database backups minimum

---

## 📞 Support

**System Health Check:**
```bash
# Check all services
curl http://localhost:8000/health
curl http://localhost:5174

# Check devices
ping 192.168.1.201
ping 192.168.1.35

# Check database
psql essl_v2 -c "SELECT COUNT(*) FROM users;"
```

**For Issues:** Check TROUBLESHOOTING.md

---

**MS Softwares - Dual Device Attendance Management System**  
Version 2.0 - Dual Device Edition
