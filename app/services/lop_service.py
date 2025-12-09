# app/services/lop_service.py
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, or_
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional
from app.models.attendance import (
    AttendanceLog, 
    ProcessedAttendance, 
    ShiftType, 
    AttendanceStatus
)
from app.models.user import User


class LOPService:
    """
    Service to detect and mark Loss of Pay (LOP) for absent employees
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_absentees_for_date(self, target_date: date) -> Dict:
        """
        Check absentees for a specific date across all 4 shifts
        """
        all_users = self.db.query(User).filter(User.is_active == True).all()
        
        attended_users = self.db.query(ProcessedAttendance.uid).filter(
            ProcessedAttendance.date == target_date
        ).distinct().all()
        
        attended_uids = {uid[0] for uid in attended_users}
        
        absentees = []
        for user in all_users:
            if user.uid not in attended_uids:
                absentees.append({
                    "uid": user.uid,
                    "name": user.name,
                    "card_no": user.card_no,
                    "date": target_date.isoformat()
                })
        
        return {
            "date": target_date.isoformat(),
            "total_employees": len(all_users),
            "present_employees": len(attended_uids),
            "absent_employees": len(absentees),
            "absentees": absentees
        }
    
    def mark_lop_for_date(self, target_date: date, exclude_uids: List[int] = None) -> Dict:
        """
        Mark LOP for all absentees on a specific date
        """
        exclude_uids = exclude_uids or []
        
        absentee_data = self.get_absentees_for_date(target_date)
        
        marked_count = 0
        skipped_count = 0
        errors = []
        
        for absentee in absentee_data["absentees"]:
            uid = absentee["uid"]
            
            if uid in exclude_uids:
                skipped_count += 1
                continue
            
            try:
                existing = self.db.query(ProcessedAttendance).filter(
                    and_(
                        ProcessedAttendance.uid == uid,
                        ProcessedAttendance.date == target_date,
                        ProcessedAttendance.status == AttendanceStatus.LOP
                    )
                ).first()
                
                if existing:
                    skipped_count += 1
                    continue
                
                lop_record = ProcessedAttendance(
                    uid=uid,
                    date=target_date,
                    shift=None,
                    first_in=None,
                    last_out=None,
                    work_duration_hours=0.0,
                    status=AttendanceStatus.LOP,
                    is_late=False,
                    is_early_leave=False,
                    late_by_minutes=0,
                    early_leave_by_minutes=0,
                    total_punches=0,
                    remarks="Loss of Pay - No attendance recorded in any shift"
                )
                
                self.db.add(lop_record)
                marked_count += 1
                
            except Exception as e:
                errors.append({"uid": uid, "error": str(e)})
        
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": f"Failed to commit LOP records: {str(e)}",
                "marked": 0,
                "skipped": 0,
                "errors": errors
            }
        
        return {
            "status": "success",
            "date": target_date.isoformat(),
            "total_absentees": len(absentee_data["absentees"]),
            "marked": marked_count,
            "skipped": skipped_count,
            "errors": errors
        }
    
    def get_lop_records(
        self, 
        start_date: Optional[date] = None, 
        end_date: Optional[date] = None,
        uid: Optional[int] = None
    ) -> List[Dict]:
        """
        Get all LOP records within a date range
        """
        query = self.db.query(ProcessedAttendance).join(User).filter(
            ProcessedAttendance.status == AttendanceStatus.LOP
        )
        
        if uid:
            query = query.filter(ProcessedAttendance.uid == uid)
        
        if start_date:
            query = query.filter(ProcessedAttendance.date >= start_date)
        
        if end_date:
            query = query.filter(ProcessedAttendance.date <= end_date)
        
        records = query.order_by(ProcessedAttendance.date.desc()).all()
        
        return [
            {
                "id": rec.id,
                "uid": rec.uid,
                "name": rec.user.name if rec.user else "Unknown",
                "date": rec.date.isoformat(),
                "remarks": rec.remarks,
                "created_at": rec.created_at.isoformat() if rec.created_at else None
            }
            for rec in records
        ]
    
    def get_lop_summary(self, uid: int, start_date: date, end_date: date) -> Dict:
        """
        Get LOP summary for a specific user
        """
        user = self.db.query(User).filter(User.uid == uid).first()
        if not user:
            return {"error": f"User with UID {uid} not found"}
        
        lop_records = self.db.query(ProcessedAttendance).filter(
            and_(
                ProcessedAttendance.uid == uid,
                ProcessedAttendance.status == AttendanceStatus.LOP,
                ProcessedAttendance.date >= start_date,
                ProcessedAttendance.date <= end_date
            )
        ).order_by(ProcessedAttendance.date).all()
        
        total_days = (end_date - start_date).days + 1
        lop_count = len(lop_records)
        lop_dates = [rec.date.isoformat() for rec in lop_records]
        
        return {
            "uid": uid,
            "name": user.name,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "total_days": total_days
            },
            "lop_summary": {
                "total_lop_days": lop_count,
                "lop_percentage": round((lop_count / total_days * 100), 2) if total_days > 0 else 0,
                "lop_dates": lop_dates
            }
        }
    
    def remove_lop_marking(self, uid: int, target_date: date, reason: str = None) -> Dict:
        """
        Remove LOP marking for a user on a specific date
        """
        lop_record = self.db.query(ProcessedAttendance).filter(
            and_(
                ProcessedAttendance.uid == uid,
                ProcessedAttendance.date == target_date,
                ProcessedAttendance.status == AttendanceStatus.LOP
            )
        ).first()
        
        if not lop_record:
            return {
                "status": "error",
                "message": f"No LOP record found for UID {uid} on {target_date.isoformat()}"
            }
        
        try:
            lop_record.status = AttendanceStatus.ABSENT
            lop_record.remarks = f"LOP removed: {reason}" if reason else "LOP removed"
            lop_record.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            return {
                "status": "success",
                "message": f"LOP removed for UID {uid} on {target_date.isoformat()}",
                "uid": uid,
                "date": target_date.isoformat(),
                "reason": reason
            }
        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": f"Failed to remove LOP: {str(e)}"
            }