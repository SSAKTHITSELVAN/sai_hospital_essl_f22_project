# MS Softwares - Dual ESSL F22 Attendance System

**Simple, powerful attendance tracking with two biometric devices**

---

## 🎯 What This System Does

- **Device 1 (Entry Device)** → Records all CHECK-IN punches
- **Device 2 (Exit Device)** → Records all CHECK-OUT punches  
- Users registered on both devices with **same name** (UID can differ)
- Supports **Regular Shift** (1 IN + 1 OUT) and **Break Shift** (2 INs + 2 OUTs)
- Auto-sync every 5 minutes
- MS Excel reports compatible with Microsoft Office

---

## 📱 Quick Start

### 1. **Install Dependencies**

```bash
# Backend (Python)
cd /path/to/project
source ../billion/bin/activate
pip install -r requirements.txt

# Frontend (React)
cd frontend
npm install
```

### 2. **Configure Devices**

Edit `.env` file:

```env
# Device 1 - Entry/IN Device
DEVICE_1_IP=192.168.1.201
DEVICE_1_PORT=4370

# Device 2 - Exit/OUT Device  
DEVICE_2_IP=192.168.1.35
DEVICE_2_PORT=4370

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=essl_v2
DB_USER=postgres
DB_PASS=your_password

# Sync Interval (in minutes)
SYNC_INTERVAL_MINUTES=5
```

### 3. **Setup Database**

```bash
# Create database
createdb essl_v2

# Run migration (add device_ip column)
psql essl_v2 < migrations/add_device_ip_column.sql
```

### 4. **Run Application**

```bash
# Start Backend
source ../billion/bin/activate
python run.py

# Start Frontend (in another terminal)
cd frontend
npm run dev
```

**Access:**
- Frontend: http://localhost:5174
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## 🔧 How It Works

### **Dual Device System**

```
Employee "John Smith" registered on BOTH devices:
├─ Device 1 (IN)  - UID: 5  - Records: Entry punches
└─ Device 2 (OUT) - UID: 21 - Records: Exit punches

System matches by NAME, not UID!
```

### **Regular Shift**
```
Device 1 (IN):  09:00 AM
Device 2 (OUT): 06:00 PM
Result: 1 session, 9 hours worked
```

### **Break Shift**
```
Session 1:
  Device 1 (IN):  08:00 AM
  Device 2 (OUT): 12:00 PM

Session 2:
  Device 1 (IN):  01:00 PM
  Device 2 (OUT): 06:00 PM

Result: 2 sessions, 9 hours worked
```

### **Status Calculation**
- **Present**: ≥ 9.0 hours
- **Half Day**: ≥ 4.5 hours and < 9.0 hours
- **Incomplete**: < 4.5 hours OR missing IN/OUT

---

## 📊 Features

### **Dashboard**
- Live device status (both devices)
- Today's attendance summary
- Quick stats (Present, Half-Day, Incomplete)
- Export to Excel

### **Employees**
- View all employees
- Search by name or UID
- Shows: UID, Name, Privilege, Status, Date Added

### **Attendance**
- Select any date (defaults to today)
- See all punch sessions (1 or 2)
- View work hours
- Export daily report

### **Payroll**
- Select date range
- Employee-wise summary
- Days present, half-day, incomplete
- Total work hours
- Regular vs Break Shift days
- Export to Excel

---

## 🔄 Data Flow

```
1. Employee punches on Device 1 (Entry)
   ↓
2. Device stores punch locally
   ↓
3. Background sync (every 5 min) fetches punches
   ↓
4. System tags punch with device_ip (192.168.1.201)
   ↓
5. Matches user by NAME (not UID)
   ↓
6. Stores as IN punch in database
   ↓
7. Same process for Device 2 → OUT punch
   ↓
8. Processor pairs IN→OUT chronologically
   ↓
9. Displays in UI with all sessions
```

---

## ⚙️ Configuration

### **Sync Interval**
Change how often punches sync from devices:

```env
SYNC_INTERVAL_MINUTES=1   # Every 1 minute (fast)
SYNC_INTERVAL_MINUTES=5   # Every 5 minutes (default)
SYNC_INTERVAL_MINUTES=10  # Every 10 minutes (slower)
```

### **Work Hours**
Adjust thresholds for status calculation:

```env
PRESENT_HOURS=9.0      # Full day threshold
HALF_DAY_HOURS=4.5     # Half day threshold
```

### **Day Boundary**
When does a new day start? (for night shifts):

```env
DAY_START_TIME=08:00   # Day starts at 8:00 AM
```

---

## 📤 Excel Exports

All exports are in `.xlsx` format (MS Office compatible):

1. **Today's Attendance**
   - Employee name, IN/OUT times, work hours, status
   - File: `Attendance_YYYY-MM-DD.xlsx`

2. **Payroll Report**
   - Date range summary per employee
   - Days present, half-day, total hours
   - File: `Payroll_YYYY-MM-DD_to_YYYY-MM-DD.xlsx`

3. **Detailed Report** (per user)
   - Daily breakdown with sessions
   - File: `Attendance_UID{X}_YYYY-MM-DD_to_YYYY-MM-DD.xlsx`

---

## 🔍 Troubleshooting

### **Problem: Device shows offline**
**Solution:**
1. Check device IP is reachable: `ping 192.168.1.201`
2. Check device port is open
3. Verify .env file has correct IPs
4. Click refresh button in UI

### **Problem: Punch takes long to appear**
**Solution:**
- Current sync interval: 5 minutes
- Reduce to 1 minute in .env: `SYNC_INTERVAL_MINUTES=1`
- Restart backend: `python run.py`

### **Problem: User shows duplicate records**
**Solution:**
- System matches by NAME
- Check if same person registered with different names
- Example: "John" vs "John Smith" = 2 different users
- Keep names consistent across both devices

### **Problem: Missing IN or OUT punch**
**Solution:**
- Employee must punch on BOTH devices
- Device 1 for IN, Device 2 for OUT
- Check device_ip in database to verify

### **Problem: Wrong work hours**
**Solution:**
1. Check DAY_START_TIME in .env (for night shifts)
2. Verify both devices have correct time
3. Check attendance_logs table for device_ip field

---

## 🗄️ Database Structure

### **Users Table**
- Stores unified user list
- Matched by NAME across devices

### **Attendance Logs Table**
- Raw punches from devices
- **device_ip** column identifies source
- Device 1 IP = IN punch
- Device 2 IP = OUT punch

### **Processed Attendance Table**
- Calculated daily attendance
- **punch_sessions** JSON field stores all sessions
- Regular vs Break Shift detected automatically

---

## 🛠️ Technical Stack

**Backend:**
- Python 3.14
- FastAPI (REST API)
- SQLAlchemy (ORM)
- PostgreSQL (Database)
- pyzk (ESSL device communication)
- openpyxl (Excel export)

**Frontend:**
- React 19
- Vite (Build tool)
- TailwindCSS (Styling)
- Axios (HTTP client)
- Lucide React (Icons)

---

## 📞 Support

**Common Issues:**
- Device connection → Check IP and port
- Sync delay → Reduce SYNC_INTERVAL_MINUTES
- User not found → Register on both devices with SAME NAME
- Missing punch → Check device status

**For More Help:**
- Check API docs: http://localhost:8000/docs
- View logs: Check terminal output
- Database check: Query attendance_logs table

---

## 📝 Important Notes

1. **Name Matching**: Users MUST have the same name on both devices
2. **Device Assignment**: 
   - Device 1 (192.168.1.201) = IN only
   - Device 2 (192.168.1.35) = OUT only
3. **Punch Modes Ignored**: System ignores device punch modes (IN/OUT/Overtime)
4. **Auto Detection**: Regular vs Break Shift detected automatically
5. **Sync Interval**: Default 5 minutes (configurable)

---

## 🚀 Quick Commands

```bash
# Start backend
python run.py

# Start frontend
cd frontend && npm run dev

# Run migration
psql essl_v2 < migrations/add_device_ip_column.sql

# Test dual device sync
python test_dual_device_sync.py

# Check database
psql essl_v2 -c "SELECT * FROM attendance_logs WHERE device_ip IS NOT NULL LIMIT 10;"
```

---

## 📄 License

MIT License - © 2026 MS Softwares

---

**MS Softwares - Dual Device Attendance Management System**  
Simple. Reliable. Efficient.
