from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import models
import secrets

router = APIRouter(prefix="/share", tags=["share"])

# Temporary storage for share tokens (should be in DB in production)
share_tokens = {}

@router.get("/generate/{user_id}")
def generate_share_link(user_id: int):
    token = secrets.token_urlsafe(16)
    share_tokens[token] = user_id
    return {"share_url": f"http://localhost:3000/public/view/{token}"}

@router.get("/view/{token}")
def view_shared_record(token: str, db: Session = Depends(get_db)):
    user_id = share_tokens.get(token)
    if not user_id:
        raise HTTPException(status_code=404, detail="Invalid or expired share link")
    
    # Return user's health summary publicly
    user = db.query(models.User).filter(models.User.id == user_id).first()
    records = db.query(models.MedicalRecord).filter(models.MedicalRecord.user_id == user_id).all()
    
    return {
        "patient_name": user.name if user else "Unknown",
        "records": records
    }
