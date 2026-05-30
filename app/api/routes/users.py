# # app/api/routes/users.py
# from fastapi import APIRouter, Depends, HTTPException, Query
# from sqlalchemy.orm import Session
# from typing import List
# from app.core.database import get_db
# from app.core.response import success_response, error_response
# from app.models.user import User

# router = APIRouter(prefix="/users", tags=["Users"])


# @router.get("")
# async def get_all_users(
#     skip: int = Query(0, ge=0),
#     limit: int = Query(100, ge=1, le=500),
#     db: Session = Depends(get_db)
# ):
#     """Get all users with pagination"""
#     try:
#         users = db.query(User).offset(skip).limit(limit).all()
#         total = db.query(User).count()
        
#         return success_response(
#             message=f"Retrieved {len(users)} users",
#             data={
#                 "users": [
#                     {
#                         "id": u.id,
#                         "uid": u.uid,
#                         "name": u.name,
#                         "privilege": u.privilege,
#                         "card_no": u.card_no,
#                         "is_active": u.is_active,
#                         "created_at": u.created_at.isoformat() if u.created_at else None
#                     }
#                     for u in users
#                 ],
#                 "pagination": {
#                     "skip": skip,
#                     "limit": limit,
#                     "total": total
#                 }
#             }
#         )
#     except Exception as e:
#         return error_response(
#             message="Failed to retrieve users",
#             error_details={"error": str(e)}
#         )


# @router.get("/{uid}")
# async def get_user_by_uid(
#     uid: int,
#     db: Session = Depends(get_db)
# ):
#     """Get user by UID"""
#     try:
#         user = db.query(User).filter(User.uid == uid).first()
        
#         if not user:
#             return error_response(
#                 message=f"User with UID {uid} not found",
#                 error_details={"uid": uid}
#             )
        
#         return success_response(
#             message="User found",
#             data={
#                 "id": user.id,
#                 "uid": user.uid,
#                 "name": user.name,
#                 "privilege": user.privilege,
#                 "card_no": user.card_no,
#                 "group_id": user.group_id,
#                 "is_active": user.is_active,
#                 "created_at": user.created_at.isoformat() if user.created_at else None,
#                 "updated_at": user.updated_at.isoformat() if user.updated_at else None
#             }
#         )
#     except Exception as e:
#         return error_response(
#             message="Failed to retrieve user",
#             error_details={"error": str(e)}
#         )




# app/api/routes/users.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.core.database import get_db
from app.core.response import success_response, error_response
from app.models.user import User

router = APIRouter(prefix="/users", tags=["Users"])


class UserUpdateRequest(BaseModel):
    name:      Optional[str]  = Field(None, min_length=1, max_length=100)
    privilege: Optional[int]  = Field(None, ge=0, le=14)
    card_no:   Optional[str]  = None
    is_active: Optional[bool] = None


@router.get("")
async def get_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=10000),
    include_inactive: bool = Query(False, description="Include soft-deleted users"),
    db: Session = Depends(get_db)
):
    """Get all users with pagination. By default returns only active users."""
    try:
        query = db.query(User)

        # Only return active users by default
        if not include_inactive:
            query = query.filter(User.is_active == True)

        total = query.count()
        users = query.offset(skip).limit(limit).all()

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
    """Get user by UID (only active users)"""
    try:
        user = db.query(User).filter(User.uid == uid, User.is_active == True).first()

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


@router.delete("/{uid}")
async def delete_user(
    uid: int,
    db: Session = Depends(get_db)
):
    """
    Soft-delete a user by UID.
    Sets is_active=False — does NOT remove from database so attendance
    history is preserved. The user will no longer appear in active listings
    or be counted in LOP absentee checks.
    """
    try:
        user = db.query(User).filter(User.uid == uid, User.is_active == True).first()

        if not user:
            return error_response(
                message=f"Active user with UID {uid} not found",
                error_details={"uid": uid}
            )

        user.is_active = False
        db.commit()

        return success_response(
            message=f"User '{user.name}' (UID {uid}) deleted successfully",
            data={"uid": uid, "name": user.name}
        )
    except Exception as e:
        db.rollback()
        return error_response(
            message="Failed to delete user",
            error_details={"error": str(e)}
        )


@router.put("/{uid}")
async def update_user(
    uid: int,
    payload: UserUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update name, card_no, privilege, or active status of a user."""
    try:
        user = db.query(User).filter(User.uid == uid, User.is_active == True).first()
        if not user:
            return error_response(
                message=f"Active user with UID {uid} not found",
                error_details={"uid": uid}
            )

        if payload.name      is not None: user.name      = payload.name
        if payload.privilege is not None: user.privilege = payload.privilege
        if payload.card_no   is not None: user.card_no   = payload.card_no
        if payload.is_active is not None: user.is_active = payload.is_active
        user.updated_at = datetime.utcnow()
        db.commit()

        return success_response(
            message=f"User '{user.name}' updated successfully",
            data={
                "uid": user.uid, "name": user.name,
                "privilege": user.privilege, "card_no": user.card_no,
                "is_active": user.is_active,
            }
        )
    except Exception as e:
        db.rollback()
        return error_response("Failed to update user", {"error": str(e)})