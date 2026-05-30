# Attendance Rules & Business Logic

## Attendance Status Rules

### Status Calculation Logic

The system calculates attendance status based on total work hours after pairing IN and OUT punches:

#### 1. PRESENT (Full Day)
- **Condition:** Total work hours ≥ 9.0 hours
- **Pay:** Full day salary
- **Requirements:**
  - At least ONE complete session (both IN and OUT)
  - Minimum 9 hours of work
- **Example:**
  ```
  IN-1: 9:00 AM → OUT-1: 6:00 PM = 9 hours
  Status: PRESENT ✓
  ```

#### 2. HALF_DAY
- **Condition:** Total work hours ≥ 4.5 hours AND < 9.0 hours
- **Pay:** Half day salary
- **Requirements:**
  - At least ONE complete session (both IN and OUT)
  - Between 4.5 to 9 hours of work
- **Example:**
  ```
  IN-1: 9:00 AM → OUT-1: 2:00 PM = 5 hours
  Status: HALF_DAY
  ```

#### 3. INCOMPLETE
- **Condition:** Either of:
  - Has complete session but < 4.5 hours work
  - Has IN punch but no OUT punch (session not finished)
- **Pay:** May lose pay (admin discretion)
- **Examples:**
  ```
  Case 1: Short work
  IN-1: 9:00 AM → OUT-1: 11:00 AM = 2 hours
  Status: INCOMPLETE
  
  Case 2: Missing OUT
  IN-1: 9:00 AM → OUT-1: (missing)
  Status: INCOMPLETE
  ```

#### 4. ABSENT (LOP - Loss of Pay)
- **Condition:** No punches at all for the day
- **Pay:** No pay - marked as LOP
- **Example:**
  ```
  Date: 2026-05-30
  Punches: None
  Status: ABSENT (LOP)
  ```

---

## Session Pairing Rules

### Dual Device Logic

**Device 1 (192.168.1.201) - IN Device:**
- ALL punches from this device = IN punches
- Ignores punch_type field from device
- Used when employee arrives

**Device 2 (192.168.1.35) - OUT Device:**
- ALL punches from this device = OUT punches
- Ignores punch_type field from device
- Used when employee leaves

### Pairing Algorithm

1. **Collect Punches:**
   - Fetch all logs for user on target date
   - Separate by device IP
   - Sort by timestamp

2. **Deduplicate:**
   - If multiple punches within 2 minutes, keep LATEST
   - Handles accidental duplicate swipes

3. **Pair Sessions:**
   - Match each IN with next OUT chronologically
   - Maximum 2 sessions per day
   - Orphan OUTs (before any IN) are skipped

4. **Calculate Hours:**
   - For each complete session: hours = (OUT - IN)
   - Total hours = sum of all session durations

### Session Examples

#### Regular Day (1 Session)
```
9:00 AM  Device 1 → IN-1
6:00 PM  Device 2 → OUT-1

Result: 1 session, 9 hours
Status: PRESENT
```

#### Break Shift (2 Sessions)
```
9:00 AM  Device 1 → IN-1
1:00 PM  Device 2 → OUT-1  (4 hours)
2:00 PM  Device 1 → IN-2
6:00 PM  Device 2 → OUT-2  (4 hours)

Result: 2 sessions, 8 hours total
Status: HALF_DAY
```

#### Incomplete Session
```
9:00 AM  Device 1 → IN-1
(No OUT punch)

Result: 1 incomplete session
Status: INCOMPLETE
```

---

## Work Hour Thresholds

### Configurable Settings (in .env or config.py)

```python
PRESENT_HOURS = 9.0      # Full day threshold
HALF_DAY_HOURS = 4.5     # Half day threshold
DAY_START_TIME = "04:00" # Logical day start
```

### Logical Day Concept

**Problem:** Night shift workers punch before midnight

**Solution:** Logical day boundary
- Punches before 4:00 AM belong to PREVIOUS day
- Punches after 4:00 AM belong to CURRENT day

**Example:**
```
Date: 2026-05-30

11:00 PM (May 30) Device 1 → Belongs to May 30
1:00 AM (May 31) Device 2  → Belongs to May 30
7:00 AM (May 31) Device 1  → Belongs to May 31
```

---

## User Matching Rules

### Name-Based Matching (PRIMARY)

**Why:** UIDs differ across devices, but names are unique

**Logic:**
1. Users synced from both devices
2. Matched by name (case-insensitive)
3. Each user has:
   - `device_1_uid` (UID on Device 1)
   - `device_2_uid` (UID on Device 2)
   - `uid` (primary UID, usually device_1_uid)

**Example:**
```
Device 1: UID=7, Name="Amudha"
Device 2: UID=15, Name="Amudha"

Database:
- uid: 7
- device_1_uid: 7
- device_2_uid: 15
- name: "Amudha"
```

### Attendance Log Matching

When processing attendance logs:
1. Fetch user's `device_1_uid` and `device_2_uid`
2. Match Device 1 logs by `device_1_uid`
3. Match Device 2 logs by `device_2_uid`
4. Create unified attendance record using `uid`

---

## Duplicate Prevention

### User Synchronization
- Check existing users by NAME (case-insensitive)
- Update if exists, insert if new
- Merge device UIDs

### Attendance Logs
- Check for duplicate by: (uid, timestamp, device_ip)
- Skip if already exists
- Prevents double-counting

### Deduplication Window
- 2-minute window for duplicate detection
- Keeps LATEST punch in window
- Example:
  ```
  9:00:00 AM - Punch 1
  9:01:30 AM - Punch 2 (within 2 min)
  → System keeps 9:01:30 AM only
  ```

---

## Finalization Rules

### Auto-Finalization
- Occurs 1 hour after last OUT punch
- Prevents further modifications
- Locked for payroll processing

### Conditions for Finalization
1. Has OUT punch
2. 1+ hours elapsed since OUT
3. Not already finalized

### Manual Processing
- Admin can force reprocess with `force=true`
- Skips finalization check
- Used for corrections

---

## Overtime (OT) Rules

### Overtime Calculation
- **Threshold:** Hours beyond 9.0
- **Formula:** `overtime_hours = max(0, total_hours - 9.0)`

### Status with OT
- If `overtime_hours > 0` → Status becomes `PRESENT_OT`
- Badge shows: "Present (OT)"
- Displayed separately in reports

**Example:**
```
IN: 9:00 AM → OUT: 7:00 PM = 10 hours
Regular: 9 hours
Overtime: 1 hour
Status: PRESENT_OT
```

---

## LOP (Loss of Pay) Rules

### LOP Marking
- Automatic daily check at 7:00 AM
- Checks previous day's attendance
- Marks absent employees as LOP

### LOP Criteria
- No attendance record for the date
- User is active (not soft-deleted)
- Not a weekend/holiday (if configured)

### LOP Record
```json
{
  "uid": 123,
  "date": "2026-05-30",
  "status": "lop",
  "reason": "No attendance recorded"
}
```

### Payroll Impact
- LOP days deducted from salary
- Formula: `payable_days = working_days - lop_days`

---

## Edge Cases Handled

### 1. Multiple Devices Same Time
- Rare: User punches both devices
- System uses device IP to differentiate
- Both recorded, paired chronologically

### 2. Out of Order Punches
- OUT before IN → OUT marked as orphan, skipped
- Next IN-OUT pair used

### 3. Maximum Sessions
- System limits to 2 sessions per day
- Extra punches ignored with remark
- Prevents data overflow

### 4. Same Device Multiple Times
- Employee punches IN device twice
- Deduplication keeps latest
- Or creates invalid pairing (no OUT between INs)

### 5. Device Offline
- Devices buffer punches internally
- Sync retrieves all buffered data
- No data loss

### 6. Fingerprint Not Recognized
- Employee must retry
- Admin can check device registration
- May need re-enrollment

---

## Status Priority

When multiple conditions apply:
1. PRESENT_OT (if OT exists)
2. PRESENT (if ≥9 hours)
3. HALF_DAY (if 4.5-9 hours)
4. INCOMPLETE (if <4.5 or missing OUT)
5. ABSENT (if no punches)

---

## Reporting Rules

### Daily Reports
- Show all employees with punches that day
- Include absent employees if LOP check ran
- Real-time updates every 30 seconds (frontend)

### Monthly Reports
- Aggregate by month
- Count present, half-day, absent, LOP days
- Calculate total work hours
- Export to Excel

### User Summary
- Date range reports per employee
- Detailed or summary view
- CSV export available
