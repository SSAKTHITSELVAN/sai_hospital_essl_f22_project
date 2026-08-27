# 🚀 Quick Start Guide - MS Softwares Attendance System

**Get up and running in 5 minutes!**

---

## ✅ Prerequisites

- PostgreSQL installed and running
- Python 3.10+ installed
- Node.js 18+ installed
- Two ESSL F22 devices on network

---

## 📋 Step-by-Step Setup

### **Step 1: Configure Devices**

Edit `.env` file:

```env
# Device 1 - Entry Device (IN punches)
DEVICE_1_IP=192.168.1.201

# Device 2 - Exit Device (OUT punches)
DEVICE_2_IP=192.168.1.4

# Database
DB_HOST=localhost
DB_NAME=essl_v2
DB_USER=postgres
DB_PASS=0.00
```

### **Step 2: Setup Database**

```bash
# Create database
createdb essl_v2

# Run migration
psql essl_v2 < migrations/add_device_ip_column.sql
```

### **Step 3: Install Backend**

```bash
# Activate virtual environment
source ../billion/bin/activate

# Install packages (if not already installed)
pip install -r requirements.txt
```

### **Step 4: Install Frontend**

```bash
cd frontend
npm install
```

### **Step 5: Start Everything**

**Terminal 1 - Backend:**
```bash
source ../billion/bin/activate
python run.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

### **Step 6: Access System**

Open browser:
- **Frontend**: http://localhost:5174
- **API Docs**: http://localhost:8000/docs

**Default Login:**
- Username: `admin`
- Password: `admin123`

---

## 🎯 First Time Use

### **1. Register Users on BOTH Devices**

**Important:** Use the **SAME NAME** on both devices!

Example:
- Device 1 (IN): Register "John Smith" → UID: 5
- Device 2 (OUT): Register "John Smith" → UID: 21

✅ System will match by name automatically.

### **2. Test Punch Flow**

1. Employee punches on **Device 1** (Entry) → Recorded as IN
2. Employee punches on **Device 2** (Exit) → Recorded as OUT
3. Wait up to 5 minutes for sync
4. Check Dashboard → Attendance will appear

### **3. View Reports**

- **Dashboard**: Today's summary
- **Attendance**: Select date to view daily records
- **Payroll**: Select date range for reports
- **Export**: Click Excel button to download

---

## ⚙️ Configuration Tips

### **Faster Sync** (1 minute instead of 5)

Edit `.env`:
```env
SYNC_INTERVAL_MINUTES=1
```

Restart backend: `python run.py`

### **Adjust Work Hours**

Edit `.env`:
```env
PRESENT_HOURS=9.0      # Full day = 9 hours
HALF_DAY_HOURS=4.5     # Half day = 4.5 hours
```

---

## 🔧 Quick Checks

### **Check Device Connection**

```bash
# Ping Device 1
ping 192.168.1.201

# Ping Device 2
ping 192.168.1.35
```

### **Manual Sync**

If you don't want to wait, trigger manual sync:

1. Open: http://localhost:8000/docs
2. Find: `POST /api/v1/device/sync`
3. Click "Try it out" → "Execute"

### **Check Database**

```bash
# View recent punches
psql essl_v2 -c "SELECT * FROM attendance_logs ORDER BY timestamp DESC LIMIT 10;"

# Check device IPs
psql essl_v2 -c "SELECT device_ip, COUNT(*) FROM attendance_logs GROUP BY device_ip;"
```

---

## 🆘 Common Issues

| Problem | Solution |
|---------|----------|
| Device shows offline | Check IP is reachable with `ping` |
| Punch not appearing | Wait 5 min or trigger manual sync |
| User not found | Register on BOTH devices with SAME name |
| Wrong hours | Check DAY_START_TIME in .env |
| Database error | Run migration script |

---

## 📱 Using the System

### **For Employees**
1. Punch on **Device 1** when entering (morning/after break)
2. Punch on **Device 2** when leaving (evening/before break)

### **For Admin**
1. View Dashboard for today's summary
2. Check Attendance page for specific dates
3. Use Payroll for monthly reports
4. Export to Excel for records

---

## 🎉 You're Ready!

System is now running. Employees can start punching on both devices.

**Need Help?** Check README.md for detailed documentation.

---

**MS Softwares - Making attendance tracking simple!**
