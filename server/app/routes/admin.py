from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import models
from ..utils.auth import get_current_user
from typing import List

router = APIRouter(prefix="/admin", tags=["admin"])

def require_admin(current_user: models.User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user

@router.get("/users")
def get_all_users(db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    users = db.query(models.User).all()
    # Masking passwords
    return [
        {
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "role": u.role,
            "created_at": u.created_at
        } for u in users
    ]

@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.email == "admin@gmail.com":
        raise HTTPException(status_code=400, detail="Cannot delete root admin")
        
    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}
