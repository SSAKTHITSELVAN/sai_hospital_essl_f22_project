# AI Context Documentation - MS Softwares Attendance System

## 📁 Documentation Structure

This folder contains comprehensive documentation of the entire MS Softwares Attendance Management System project. It serves as a complete knowledge base for AI assistants, developers, and system administrators.

---

## 📚 Document Index

### 1. **01_PROJECT_OVERVIEW.md**
**What it covers:**
- Project purpose and goals
- Technology stack (FastAPI, React, PostgreSQL)
- Project structure
- Key features
- Hardware integration
- Deployment architecture

**Read this first for:** Understanding what the project does and how it's built.

---

### 2. **02_ATTENDANCE_RULES.md**
**What it covers:**
- Status calculation rules (PRESENT, HALF_DAY, INCOMPLETE, ABSENT)
- Session pairing algorithm
- Dual device logic (IN/OUT)
- Work hour thresholds
- User matching rules
- Duplicate prevention
- LOP (Loss of Pay) rules
- Edge cases handling

**Read this for:** Understanding the business logic and attendance calculation rules.

---

### 3. **03_SYSTEM_ARCHITECTURE.md**
**What it covers:**
- High-level architecture diagram
- Component details (Frontend, Backend, Services, Database)
- Data flow diagrams
- User registration flow
- Attendance processing flow
- Payroll flow
- Security architecture
- Deployment models

**Read this for:** Understanding how all components work together.

---

### 4. **04_DATABASE_SCHEMA.md**
**What it covers:**
- Complete database schema
- Table structures (users, attendance_logs, processed_attendance, devices)
- Column descriptions
- Indexes and foreign keys
- Sample data
- Common queries
- Migration notes

**Read this for:** Database design, queries, and data relationships.

---

### 5. **05_API_DOCUMENTATION.md**
**What it covers:**
- All API endpoints
- Request/response formats
- Authentication methods
- Query parameters
- Error codes
- Examples for each endpoint

**Read this for:** API integration and frontend-backend communication.

---

## 🎯 Quick Reference Guide

### For New AI Assistants

**Scenario:** User asks about attendance calculation
→ Read: `02_ATTENDANCE_RULES.md`

**Scenario:** User asks about API endpoints
→ Read: `05_API_DOCUMENTATION.md`

**Scenario:** User asks about database structure
→ Read: `04_DATABASE_SCHEMA.md`

**Scenario:** User asks about overall system design
→ Read: `03_SYSTEM_ARCHITECTURE.md`

**Scenario:** User asks "What does this project do?"
→ Read: `01_PROJECT_OVERVIEW.md`

---

## 🔑 Key Concepts

### Dual Device Architecture
- **Device 1 (192.168.1.201):** IN device at entrance - records all arrivals
- **Device 2 (192.168.1.35):** OUT device at exit - records all departures
- Each user has separate UIDs on each device
- Name-based matching unifies user identity

### Attendance Status Rules
```
9+ hours     = PRESENT      (Full pay)
4.5-9 hours  = HALF_DAY     (Half pay)
< 4.5 hours  = INCOMPLETE   (May lose pay)
No punches   = ABSENT/LOP   (No pay)
```

### Session Pairing
- System pairs IN and OUT punches chronologically
- Maximum 2 sessions per day (for break shifts)
- Deduplication: 2-minute window keeps latest punch

### Data Flow
```
Employee Punch → Device → Background Sync (30s) 
→ Database → Processing → Frontend Display
```

---

## 📊 System Statistics

### Current Implementation
- **Employees Supported:** 500-1000
- **Devices:** 2 (IN and OUT)
- **Background Sync:** Every 30 seconds
- **LOP Check:** Daily at 7 AM
- **Session Expiry:** 30 minutes
- **Max Sessions per Day:** 2

### Database Tables
- `users`: Employee information
- `attendance_logs`: Raw punch data
- `processed_attendance`: Daily summaries
- `devices`: Device status tracking

### API Endpoints
- **Users:** 4 endpoints
- **Attendance:** 6 endpoints
- **Payroll:** 2 endpoints
- **Device:** 2 endpoints
- **LOP:** 2 endpoints
- **Export:** 2 endpoints
- **Auth:** 2 endpoints

---

## 🚀 Recent Changes & Migrations

### Migration: Device-Specific UIDs (May 2026)
**What changed:**
- Added `device_1_uid` and `device_2_uid` columns to `users` table
- Changed user matching from UID-based to name-based
- Fixed duplicate UID conflicts

**Migration script:** `migrate_add_device_uids.py`

**Impact:**
- Users can now have different UIDs on each device
- System correctly handles cross-device user matching
- No more duplicate UID errors during sync

### UI Improvements
1. **Live Timers:** Show elapsed time for ongoing sessions
2. **IN-1/OUT-1 Display:** Clear session breakdown
3. **Device Registration Status:** Shows which devices user is registered on
4. **Auto-refresh:** Real-time updates every 30 seconds
5. **Status Labels:** "Started" vs "Complete" instead of "Incomplete"

---

## 🔧 Configuration Files

### Environment Variables (.env)
```env
DATABASE_URL=postgresql://user:pass@localhost/db_name
DEVICE_1_IP=192.168.1.201
DEVICE_1_PORT=4370
DEVICE_2_IP=192.168.1.35
DEVICE_2_PORT=4370
DAY_START_TIME=04:00
PRESENT_HOURS=9.0
HALF_DAY_HOURS=4.5
```

### Important Files
- **Backend Entry:** `run.py` or `app/main.py`
- **Frontend Entry:** `frontend/src/main.jsx`
- **Database Models:** `app/models/`
- **API Routes:** `app/api/routes/`
- **Services:** `app/services/`

---

## 📖 Employee Documentation

### User Guides Available
1. **EMPLOYEE_GUIDE.md** - Detailed employee instructions
2. **EMPLOYEE_QUICK_GUIDE.md** - One-page quick reference
3. **MIGRATION_GUIDE.md** - Database migration instructions

---

## 🛠️ Development Workflow

### Starting the System

**Backend:**
```bash
cd /path/to/project
python run.py
```

**Frontend (Development):**
```bash
cd frontend
npm run dev
```

**Frontend (Production):**
```bash
cd frontend
npm run build
# Served by FastAPI from 'static' folder
```

### Running Migrations
```bash
python migrate_add_device_uids.py
```

### Database Operations
```bash
# Backup
pg_dump -U postgres db_name > backup.sql

# Restore
psql -U postgres db_name < backup.sql
```

---

## 🐛 Common Issues & Solutions

### Issue: "column users.device_1_uid does not exist"
**Solution:** Run the migration script `migrate_add_device_uids.py`

### Issue: 422 Error - "limit should be less than or equal to 500"
**Solution:** Already fixed - backend now accepts limit up to 10000

### Issue: Employee names showing "Unknown"
**Solution:** Already fixed - backend now sends `user_name` field

### Issue: Duplicate UID errors during sync
**Solution:** Already fixed - name-based matching with separate device UIDs

### Issue: Status shows "Incomplete" even after OUT punch
**Solution:** Already fixed - status updates when at least one session is complete

---

## 📞 Support & Maintenance

### Log Files Locations
- Backend logs: Console output or `/var/log/attendance.log`
- Database logs: PostgreSQL logs
- Device sync errors: Printed to console

### Monitoring Checklist
- [ ] Device connectivity (check Dashboard)
- [ ] Background sync running (every 30s)
- [ ] LOP check scheduled (7 AM daily)
- [ ] Database connection active
- [ ] Disk space available

### Backup Schedule
- **Daily:** Database backup
- **Weekly:** Full project backup
- **Monthly:** Archive old attendance logs

---

## 🔐 Security Notes

### Authentication
- Password-based admin login
- 30-minute session expiry
- Token stored in localStorage
- Protected API routes

### Network Security
- Devices on local network only
- Backend accessible on LAN
- No public internet exposure (current setup)

### Data Privacy
- Employee fingerprints stored on devices
- Database contains only UIDs, names, and timestamps
- No biometric data in database

---

## 📈 Future Enhancements (Potential)

### Possible Features
1. Multiple locations support
2. Role-based access control
3. Mobile app for employees
4. Real-time notifications
5. Integration with payroll software
6. Leave management
7. Shift scheduling
8. Overtime approval workflow
9. Cloud deployment
10. Multi-language support

---

## 📝 Version History

### Current Version: 1.0.0 (May 2026)
**Features:**
- Dual device support
- Name-based user matching
- Live attendance timers
- Device registration tracking
- Excel export
- LOP calculation
- Monthly payroll

**Recent Updates:**
- Device-specific UID tracking
- Improved status calculation
- Enhanced UI/UX
- Auto-refresh functionality

---

## 🤝 Contributing

### For AI Assistants
When helping users with this project:
1. Read relevant documentation first
2. Understand the dual device architecture
3. Follow attendance rules exactly
4. Consider backward compatibility
5. Document any new changes

### For Developers
1. Follow existing code structure
2. Update documentation when making changes
3. Test with both devices
4. Consider edge cases
5. Maintain database migrations

---

## 📧 Contact

**Project:** MS Softwares Attendance Management System
**Client:** Sai Hospital
**Hardware:** ESSL F22 Fingerprint Devices (x2)
**Year:** 2026

---

## 🎓 Learning Resources

### Technologies Used
- **FastAPI:** https://fastapi.tiangolo.com/
- **React:** https://react.dev/
- **SQLAlchemy:** https://www.sqlalchemy.org/
- **PostgreSQL:** https://www.postgresql.org/
- **pyzk (ZKTeco):** https://github.com/kurenai-ryu/pyzk
- **Tailwind CSS:** https://tailwindcss.com/

### Recommended Reading Order
1. Start with `01_PROJECT_OVERVIEW.md`
2. Read `02_ATTENDANCE_RULES.md` for business logic
3. Review `03_SYSTEM_ARCHITECTURE.md` for design
4. Study `04_DATABASE_SCHEMA.md` for data model
5. Reference `05_API_DOCUMENTATION.md` as needed

---

**Last Updated:** May 30, 2026
**Documentation Version:** 1.0
