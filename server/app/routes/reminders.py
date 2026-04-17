from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import models
from pydantic import BaseModel
from datetime import date

router = APIRouter(prefix="/reminders", tags=["reminders"])

from ..utils.auth import get_current_user
from typing import List

router = APIRouter(prefix="/reminders", tags=["reminders"])

class ReminderCreate(BaseModel):
    medicine_name: str
    dosage: str
    start_date: date
    end_date: date
    frequency: str

@router.post("/")
def create_reminder(reminder: ReminderCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_reminder = models.Reminder(**reminder.dict(), user_id=current_user.id)
    db.add(db_reminder)
    db.commit()
    db.refresh(db_reminder)
    return db_reminder

@router.get("/", response_model=List[dict])
def get_reminders(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.Reminder).filter(
        models.Reminder.user_id == current_user.id, 
        models.Reminder.is_active == True
    ).all()
