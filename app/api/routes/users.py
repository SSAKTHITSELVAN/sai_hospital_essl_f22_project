# app/api/routes/users.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.response import success_response, error_response
from app.models.user import User

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("")
async def get_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Get all users with pagination"""
    try:
        users = db.query(User).offset(skip).limit(limit).all()
        total = db.query(User).count()
        
        return success_response(
            message=f"Retrieved {len(users)} users",
            data={
                "users": [
                    {
                        "id": u.id,
                        "uid": u.uid,
                        "name": u.name,
                        "privilege": u.privilege,
                        "card_no": u.card_no,
                        "is_active": u.is_active,
                        "created_at": u.created_at.isoformat() if u.created_at else None
                    }
                    for u in users
                ],
                "pagination": {
                    "skip": skip,
                    "limit": limit,
                    "total": total
                }
            }
        )
    except Exception as e:
        return error_response(
            message="Failed to retrieve users",
            error_details={"error": str(e)}
        )


@router.get("/{uid}")
async def get_user_by_uid(
    uid: int,
    db: Session = Depends(get_db)
):
    """Get user by UID"""
    try:
        user = db.query(User).filter(User.uid == uid).first()
        
        if not user:
            return error_response(
                message=f"User with UID {uid} not found",
                error_details={"uid": uid}
            )
        
        return success_response(
            message="User found",
            data={
                "id": user.id,
                "uid": user.uid,
                "name": user.name,
                "privilege": user.privilege,
                "card_no": user.card_no,
                "group_id": user.group_id,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None
            }
        )
    except Exception as e:
        return error_response(
            message="Failed to retrieve user",
            error_details={"error": str(e)}
        )

