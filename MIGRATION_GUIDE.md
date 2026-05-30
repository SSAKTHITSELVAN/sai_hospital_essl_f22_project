# Database Migration Guide
## Adding Device-Specific UID Columns

## ⚠️ Important
You need to run this migration to fix the duplicate UID error and enable dual-device UID tracking.

---

## 🪟 **For Windows Users**

### Option 1: Run the Batch File (Easiest)
```batch
run_migration.bat
```

### Option 2: Run Python Script Directly
```batch
# Activate your virtual environment first
saienv\Scripts\activate

# Run migration
python migrate_add_device_uids.py
```

### Option 3: Run SQL Script Manually
If Python script fails, use pgAdmin or psql:

**Using pgAdmin:**
1. Open pgAdmin
2. Connect to your database
3. Right-click your database → Query Tool
4. Open file: `migrate_device_uids.sql`
5. Click Execute (F5)

**Using psql command:**
```bash
psql -U postgres -d your_database_name -f migrate_device_uids.sql
```

---

## 🐧 **For Linux/Mac Users**

### Option 1: Run Python Script
```bash
# Activate your virtual environment
source venv/bin/activate  # or: source saienv/bin/activate

# Run migration
python3 migrate_add_device_uids.py
```

### Option 2: Run SQL Script
```bash
psql -U postgres -d your_database_name -f migrate_device_uids.sql
```

---

## ✅ What This Migration Does

1. **Adds two new columns to `users` table:**
   - `device_1_uid` - UID from Device 1 (IN device at 192.168.1.201)
   - `device_2_uid` - UID from Device 2 (OUT device at 192.168.1.35)

2. **Creates indexes** for performance on both new columns

3. **Populates initial data** - copies existing `uid` to `device_1_uid`

4. **Makes `name` unique** - since names are the primary identifier across devices

---

## 📊 After Migration

Once migration completes, you'll see output like:
```
✅ MIGRATION COMPLETED SUCCESSFULLY!

📊 Current Users Data:
  Total users: 25
  With device_1_uid: 25
  With device_2_uid: 0

NEXT STEPS:
1. Restart your backend server
2. Run a device sync to populate device_2_uid
3. Check the frontend attendance page
```

---

## 🔄 Next Steps After Migration

### 1. Restart Backend Server
**Windows:**
```batch
# Stop current server (Ctrl+C)
# Then restart:
python run.py
```

**Linux/Mac:**
```bash
# Stop current server (Ctrl+C)
# Then restart:
python3 run.py
```

### 2. Sync Devices
The system will automatically sync devices on startup, or you can manually trigger sync via the Dashboard.

### 3. Verify
- Open the frontend
- Go to Attendance page
- Check that data loads without errors
- For today's date, you should see live timers for ongoing sessions

---

## ❌ Troubleshooting

### Error: "column users.device_1_uid does not exist"
**Solution:** You haven't run the migration yet. Follow steps above.

### Error: "ModuleNotFoundError: No module named 'sqlalchemy'"
**Solution:** Use the SQL script method (Option 3) instead.

### Error: "duplicate key value violates unique constraint"
**Solution:** After migration, the sync service will handle this automatically.

### Migration says "already exists"
**Good!** This means migration was already run. Just restart your server.

---

## 🔍 Verify Migration Success

Run this SQL query to check:
```sql
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'users'
    AND column_name IN ('uid', 'device_1_uid', 'device_2_uid', 'name');
```

You should see all four columns listed.

---

## 📝 What Changed in the Code

### Database Schema (`app/models/user.py`):
```python
class User(Base):
    uid = Column(Integer, unique=True, index=True)  # Primary UID
    device_1_uid = Column(Integer, nullable=True)   # NEW: Device 1 UID
    device_2_uid = Column(Integer, nullable=True)   # NEW: Device 2 UID
    name = Column(String(100), unique=True)         # UPDATED: Now unique
    # ... other fields
```

### Sync Logic (`app/services/device_sync.py`):
- Users now matched by NAME instead of UID
- Each device's UID stored in separate column
- Prevents duplicate UID conflicts

### Frontend (`frontend/src/pages/Attendance.jsx`):
- Live timer shows elapsed time for ongoing sessions
- Session status: "Started" (blue) or "Complete" (green)
- Auto-refresh every 30 seconds for today's date
- Active sessions counter

---

## 💡 Need Help?

If migration fails or you see errors, check:
1. Database connection (PostgreSQL running?)
2. Database credentials in `.env` file
3. Virtual environment activated
4. All dependencies installed (`pip install -r requirements.txt`)

Still stuck? Share the error message for help.
