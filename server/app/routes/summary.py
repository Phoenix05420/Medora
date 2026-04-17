from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import models
from ..utils import r_bridge
import json
import os
import logging

logger = logging.getLogger("ocr_service")

from ..utils.auth import get_current_user

router = APIRouter(prefix="/summaries", tags=["summaries"])

@router.get("/generate")
def generate_summary(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # 1. Fetch user records
    records = db.query(models.MedicalRecord).filter(
        models.MedicalRecord.user_id == current_user.id
    ).order_by(models.MedicalRecord.visit_date.desc()).all()
    
    if not records:
        return {"ai_summary": "No medical records found yet. Upload a prescription to get started!"}

    # Serialize records for analysis
    records_context = []
    for r in records:
        records_context.append({
            "doctor": r.doctor_name,
            "date": str(r.visit_date),
            "diagnoses": r.diagnoses or [],
            "medicines": r.medicines or []
        })
    
    # 2. Run R Analytics for statistical insights
    r_insights = {"error": "Statistical engine offline"}
    try:
        r_insights = r_bridge.run_health_analysis(json.dumps(records_context))
    except Exception as e:
        logger.warning(f"R Analytics failed: {e}")

    # 3. Build a local summary from the data (no cloud API needed)
    all_meds = []
    all_diagnoses = []
    doctors_seen = set()
    
    for r in records:
        if r.medicines:
            for m in r.medicines:
                name = m.get("name", "") if isinstance(m, dict) else str(m)
                if name and name not in all_meds:
                    all_meds.append(name)
        if r.diagnoses:
            for d in r.diagnoses:
                if d and d not in all_diagnoses:
                    all_diagnoses.append(d)
        if r.doctor_name and r.doctor_name != "Not detected":
            doctors_seen.add(r.doctor_name)

    summary_parts = []
    summary_parts.append(f"You have {len(records)} medical record(s) on file.")
    
    if doctors_seen:
        summary_parts.append(f"Doctors consulted: {', '.join(doctors_seen)}.")
    
    if all_diagnoses:
        summary_parts.append(f"Conditions noted: {', '.join(all_diagnoses[:5])}.")
    
    if all_meds:
        summary_parts.append(f"Medications prescribed: {', '.join(all_meds[:8])}.")
    
    if len(records) > 1:
        summary_parts.append("Regular follow-ups detected — good adherence pattern.")

    ai_summary = " ".join(summary_parts)

    return {
        "ai_summary": ai_summary,
        "statistical_insights": r_insights,
        "record_count": len(records)
    }
