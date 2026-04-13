# app/services/lop_service.py
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional

from app.models.attendance import ProcessedAttendance, AttendanceStatus
from app.models.user import User


class LOPService:

    def __init__(self, db: Session):
        self.db = db

    def get_absentees_for_date(self, target_date: date) -> Dict:
        all_users = self.db.query(User).filter(User.is_active == True).all()

        attended_uids = {
            r[0]
            for r in self.db.query(ProcessedAttendance.uid)
            .filter(
                ProcessedAttendance.date   == target_date,
                ProcessedAttendance.status != AttendanceStatus.LOP,
                ProcessedAttendance.status != AttendanceStatus.ABSENT,
            )
            .distinct()
            .all()
        }

        absentees = [
            {"uid": u.uid, "name": u.name, "card_no": u.card_no, "date": target_date.isoformat()}
            for u in all_users
            if u.uid not in attended_uids
        ]

        return {
            "date":               target_date.isoformat(),
            "total_employees":    len(all_users),
            "present_employees":  len(attended_uids),
            "absent_employees":   len(absentees),
            "absentees":          absentees,
        }

    def mark_lop_for_date(
        self,
        target_date: date,
        exclude_uids: List[int] = None,
    ) -> Dict:
        exclude_uids  = exclude_uids or []
        absentee_data = self.get_absentees_for_date(target_date)

        marked_count = skipped_count = 0
        errors = []

        for absentee in absentee_data["absentees"]:
            uid = absentee["uid"]
            if uid in exclude_uids:
                skipped_count += 1
                continue
            try:
                exists = self.db.query(ProcessedAttendance).filter(
                    ProcessedAttendance.uid    == uid,
                    ProcessedAttendance.date   == target_date,
                    ProcessedAttendance.status == AttendanceStatus.LOP,
                ).first()
                if exists:
                    skipped_count += 1
                    continue

                lop = ProcessedAttendance(
                    uid=uid, date=target_date, shift=None,
                    first_in=None, last_out=None,
                    work_duration_hours=0.0, overtime_hours=0.0,
                    status=AttendanceStatus.LOP,
                    is_late=False, is_early_leave=False,
                    late_by_minutes=0, early_leave_by_minutes=0,
                    total_punches=0,
                    remarks="Loss of Pay — no attendance recorded",
                )
                self.db.add(lop)
                marked_count += 1
            except Exception as e:
                errors.append({"uid": uid, "error": str(e)})

        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e), "marked": 0, "skipped": 0, "errors": errors}

        return {
            "status":          "success",
            "date":            target_date.isoformat(),
            "total_absentees": len(absentee_data["absentees"]),
            "marked":          marked_count,
            "skipped":         skipped_count,
            "errors":          errors,
        }

    def get_lop_records(
        self,
        start_date: Optional[date] = None,
        end_date:   Optional[date] = None,
        uid:        Optional[int]  = None,
    ) -> List[Dict]:
        query = self.db.query(ProcessedAttendance).join(User).filter(
            ProcessedAttendance.status == AttendanceStatus.LOP
        )
        if uid:        query = query.filter(ProcessedAttendance.uid  == uid)
        if start_date: query = query.filter(ProcessedAttendance.date >= start_date)
        if end_date:   query = query.filter(ProcessedAttendance.date <= end_date)

        records = query.order_by(ProcessedAttendance.date.desc()).all()
        return [
            {
                "id":         r.id,
                "uid":        r.uid,
                "name":       r.user.name if r.user else "Unknown",
                "date":       r.date.isoformat(),
                "remarks":    r.remarks,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ]

    def get_lop_summary(self, uid: int, start_date: date, end_date: date) -> Dict:
        user = self.db.query(User).filter(User.uid == uid).first()
        if not user:
            return {"error": f"User with UID {uid} not found"}

        lop_records = self.db.query(ProcessedAttendance).filter(
            ProcessedAttendance.uid    == uid,
            ProcessedAttendance.status == AttendanceStatus.LOP,
            ProcessedAttendance.date   >= start_date,
            ProcessedAttendance.date   <= end_date,
        ).order_by(ProcessedAttendance.date).all()

        total_days = (end_date - start_date).days + 1
        lop_count  = len(lop_records)

        return {
            "uid":  uid,
            "name": user.name,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date":   end_date.isoformat(),
                "total_days": total_days,
            },
            "lop_summary": {
                "total_lop_days": lop_count,
                "lop_percentage": round(lop_count / total_days * 100, 2) if total_days else 0,
                "lop_dates":      [r.date.isoformat() for r in lop_records],
            },
        }

    def remove_lop_marking(self, uid: int, target_date: date, reason: str = None) -> Dict:
        rec = self.db.query(ProcessedAttendance).filter(
            ProcessedAttendance.uid    == uid,
            ProcessedAttendance.date   == target_date,
            ProcessedAttendance.status == AttendanceStatus.LOP,
        ).first()

        if not rec:
            return {"status": "error", "message": f"No LOP record for UID {uid} on {target_date}"}

        try:
            rec.status     = AttendanceStatus.ABSENT
            rec.remarks    = f"LOP removed: {reason}" if reason else "LOP removed"
            rec.updated_at = datetime.utcnow()
            self.db.commit()
            return {"status": "success", "message": f"LOP removed for UID {uid} on {target_date}", "uid": uid, "date": str(target_date)}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}