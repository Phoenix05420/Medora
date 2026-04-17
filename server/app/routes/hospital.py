from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import models
from ..utils.auth import get_current_user

router = APIRouter(prefix="/hospital", tags=["hospital"])

def require_hospital(current_user: models.User = Depends(get_current_user)):
    if current_user.role != "hospital":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hospital privileges required"
        )
    return current_user

@router.get("/alerts")
def get_hospital_alerts(db: Session = Depends(get_db), current_user: models.User = Depends(require_hospital)):
    # Get alerts matched to this hospital
    alerts = db.query(models.EmergencyAlert).filter(models.EmergencyAlert.hospital_id == current_user.id).all()
    return alerts

@router.get("/appointments")
def get_appointments(db: Session = Depends(get_db), current_user: models.User = Depends(require_hospital)):
    appointments = db.query(models.Appointment).filter(models.Appointment.hospital_id == current_user.id).all()
    return appointments

@router.put("/profile")
def update_profile(data: dict, db: Session = Depends(get_db), current_user: models.User = Depends(require_hospital)):
    profile = db.query(models.HospitalProfile).filter(models.HospitalProfile.user_id == current_user.id).first()
    if not profile:
        profile = models.HospitalProfile(user_id=current_user.id, specializations=[])
        db.add(profile)
        
    profile.lat = data.get("lat", profile.lat)
    profile.lng = data.get("lng", profile.lng)
    profile.address = data.get("address", profile.address)
    profile.specializations = data.get("specializations", profile.specializations)
    
    db.commit()
    return {"message": "Profile updated"}
