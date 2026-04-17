from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import models
from ..utils.auth import get_current_user
import math

router = APIRouter(prefix="/emergency", tags=["emergency"])

class AlertRequest(BaseModel):
    category: str
    lat: str
    lng: str

def get_distance(lat1, lon1, lat2, lon2):
    # Haversine formula
    R = 6371  # Radius of earth in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2) * math.sin(dlat/2) + \
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
        math.sin(dlon/2) * math.sin(dlon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

@router.post("/alert")
def dispatch_alert(req: AlertRequest, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # Map category to specialization
    cat_map = {
        "heart pain": "cardio",
        "road accident": "trauma",
        "severe bleeding": "trauma",
        "stroke": "neuro"
    }
    required_spec = cat_map.get(req.category.lower(), "multispecialist")

    # Find nearest capable hospital
    hospitals = db.query(models.HospitalProfile).all()
    closest = None
    min_dist = float('inf')

    for h in hospitals:
        specs = h.specializations or []
        if required_spec in specs or "multispecialist" in specs:
            try:
                dist = get_distance(float(req.lat), float(req.lng), float(h.lat), float(h.lng))
                if dist < min_dist:
                    min_dist = dist
                    closest = h
            except ValueError:
                pass
    
    if not closest:
        # Fallback to any hospital
        if hospitals:
            closest = hospitals[0]
        else:
            raise HTTPException(status_code=404, detail="No suitable hospitals found in the network.")

    # Dispatch alert
    alert = models.EmergencyAlert(
        patient_id=current_user.id,
        hospital_id=closest.user_id,
        category=req.category,
        lat=req.lat,
        lng=req.lng,
        status="pending"
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    # Fetch hospital details to return
    h_user = db.query(models.User).filter(models.User.id == closest.user_id).first()

    return {
        "message": "Alert Dispatched",
        "hospital_id": closest.user_id,
        "hospital_name": h_user.name if h_user else "Unknown Hospital",
        "distance_km": round(min_dist, 1) if min_dist != float('inf') else 0,
        "alert_id": alert.id
    }
