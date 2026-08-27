# 🔧 Troubleshooting Guide - MS Softwares Attendance System

**Quick solutions to common problems**

---

## 🔴 Device Connection Issues

### **Problem: Device shows "Offline" in UI**

**Check 1: Network Connection**
```bash
# Test Device 1
ping 192.168.1.201

# Test Device 2
ping 192.168.1.35
```

✅ **If ping works:** Device is reachable  
❌ **If ping fails:** Check network cable, device power, IP address

**Check 2: Verify IP in .env**
```bash
cat .env | grep DEVICE
```

Should show:
```
DEVICE_1_IP=192.168.1.201
DEVICE_2_IP=192.168.1.4
```

**Check 3: Device Status**
- Open: http://localhost:8000/docs
- Try: `GET /api/v1/device/info`
- Click "Execute"
- Check response for device details

**Solution:**
1. Verify device IPs are correct
2. Check device is powered on
3. Ensure devices are on same network as server
4. Click refresh button in UI

---

## ⏱️ Punch Delay Issues

### **Problem: Punch takes 5+ minutes to appear**

**Why:** Background sync runs every 5 minutes by default.

**Solution: Speed Up Sync**

Edit `.env`:
```env
SYNC_INTERVAL_MINUTES=1   # Sync every 1 minute
```

Restart backend:
```bash
python run.py
```

**Manual Sync (Instant):**
1. Go to: http://localhost:8000/docs
2. Find: `POST /api/v1/device/sync`
3. Click "Try it out" → "Execute"
4. Refresh UI

---

## 👤 User/Employee Issues

### **Problem: User not found / No attendance recorded**

**Cause:** User not registered on both devices OR different names used.

**Solution:**

**Check 1: User must exist on BOTH devices**
- Register on Device 1 (IN device)
- Register on Device 2 (OUT device)
- **Use EXACT SAME NAME on both!**

**Example - CORRECT:**
```
Device 1: "John Smith" (UID: 5)
Device 2: "John Smith" (UID: 21)  ✅ Same name
```

**Example - WRONG:**
```
Device 1: "John Smith" (UID: 5)
Device 2: "John" (UID: 21)  ❌ Different names
```

**Check 2: Verify in database**
```bash
psql essl_v2 -c "SELECT uid, name FROM users WHERE is_active=true;"
```

---

## 📊 Attendance Data Issues

### **Problem: Missing IN or OUT punch**

**Cause:** Employee only punched on one device.

**Solution:**
- Employee MUST punch on BOTH devices
- Device 1 for IN (entry)
- Device 2 for OUT (exit)

**Check which device has punch:**
```bash
psql essl_v2 -c "SELECT u.name, a.timestamp, a.device_ip FROM attendance_logs a JOIN users u ON a.uid = u.uid WHERE u.name = 'John Smith' ORDER BY timestamp DESC LIMIT 10;"
```

Look at `device_ip`:
- `192.168.1.201` = IN punch (Device 1)
- `192.168.1.35` = OUT punch (Device 2)

---

### **Problem: Wrong work hours calculated**

**Check 1: All sessions shown?**

For Break Shift users, should see 2 sessions:
```
Session 1: IN 08:00 AM → OUT 12:00 PM
Session 2: IN 01:00 PM → OUT 06:00 PM
```

**Check 2: Day boundary correct?**

For night shift workers, check `.env`:
```env
DAY_START_TIME=04:00
```

If night shift ends at 7 AM, use 08:00.  
If night shift ends at 11 PM, use 00:00.

**Check 3: Device times synchronized?**

Both devices must have same time. Check device settings.

---

## 💾 Database Issues

### **Problem: Database connection failed**

**Check 1: PostgreSQL running?**
```bash
sudo systemctl status postgresql
```

**If stopped:**
```bash
sudo systemctl start postgresql
```

**Check 2: Database exists?**
```bash
psql -l | grep essl_v2
```

**If not found:**
```bash
createdb essl_v2
```

**Check 3: Run migration**
```bash
psql essl_v2 < migrations/add_device_ip_column.sql
```

---

### **Problem: Missing device_ip column**

**Error:** Column "device_ip" does not exist

**Solution:**
```bash
psql essl_v2 < migrations/add_device_ip_column.sql
```

Or manually:
```sql
ALTER TABLE attendance_logs ADD COLUMN IF NOT EXISTS device_ip VARCHAR(50);
CREATE INDEX IF NOT EXISTS idx_attendance_logs_device_ip ON attendance_logs(device_ip);
```

---

## 🖥️ Frontend Issues

### **Problem: Frontend won't start**

**Check 1: Dependencies installed?**
```bash
cd frontend
npm install
```

**Check 2: Port 5173/5174 already in use?**
```bash
lsof -i :5173
lsof -i :5174
```

**Kill process if needed:**
```bash
kill -9 <PID>
```

**Start again:**
```bash
npm run dev
```

---

### **Problem: API calls failing**

**Check 1: Backend running?**

Backend should be on: http://localhost:8000

Test:
```bash
curl http://localhost:8000/health
```

**Check 2: CORS issue?**

Check browser console (F12) for CORS errors.

Backend already has CORS enabled for all origins.

---

## 📤 Export Issues

### **Problem: Excel export fails**

**Check 1: openpyxl installed?**
```bash
source ../billion/bin/activate
pip install openpyxl
```

**Check 2: Data exists?**

Check if there's data for selected date:
```bash
psql essl_v2 -c "SELECT COUNT(*) FROM processed_attendance WHERE date = CURRENT_DATE;"
```

---

## 🔄 Sync Issues

### **Problem: Duplicate punches appearing**

**Cause:** Same punch synced multiple times.

**Solution:** System automatically prevents duplicates.

**Check for actual duplicates:**
```bash
psql essl_v2 -c "SELECT uid, timestamp, device_ip, COUNT(*) FROM attendance_logs GROUP BY uid, timestamp, device_ip HAVING COUNT(*) > 1;"
```

**If duplicates found, remove:**
```sql
DELETE FROM attendance_logs a USING attendance_logs b 
WHERE a.id > b.id 
AND a.uid = b.uid 
AND a.timestamp = b.timestamp 
AND a.device_ip = b.device_ip;
```

---

## 🆘 Emergency Commands

### **Reset Everything**

**⚠️ WARNING: Deletes all attendance data!**

```bash
psql essl_v2 <<EOF
TRUNCATE TABLE attendance_logs CASCADE;
TRUNCATE TABLE processed_attendance CASCADE;
TRUNCATE TABLE users CASCADE;
EOF
```

### **View Recent Logs**

```bash
# Last 20 punches
psql essl_v2 -c "SELECT u.name, a.timestamp, a.device_ip FROM attendance_logs a JOIN users u ON a.uid = u.uid ORDER BY a.timestamp DESC LIMIT 20;"

# Today's processed attendance
psql essl_v2 -c "SELECT u.name, p.first_in, p.last_out, p.work_duration_hours, p.status FROM processed_attendance p JOIN users u ON p.uid = u.uid WHERE p.date = CURRENT_DATE;"
```

### **Check Sync Status**

```bash
psql essl_v2 -c "SELECT device_ip, last_sync_at, last_sync_status FROM devices;"
```

### **Force Re-process Attendance**

```bash
# Delete processed records for today
psql essl_v2 -c "DELETE FROM processed_attendance WHERE date = CURRENT_DATE;"

# Trigger manual sync (will re-process)
curl -X POST http://localhost:8000/api/v1/device/sync
```

---

## 📞 Still Need Help?

1. **Check Logs:**
   - Backend terminal output
   - Browser console (F12)

2. **Test API Directly:**
   - http://localhost:8000/docs
   - Try endpoints manually

3. **Verify Configuration:**
   - Check `.env` file
   - Confirm device IPs
   - Check database credentials

4. **Database Inspection:**
   ```bash
   psql essl_v2
   \dt              # List tables
   \d+ attendance_logs  # Show table structure
   ```

---

**MS Softwares - We're here to help!**

For more details, check README.md
