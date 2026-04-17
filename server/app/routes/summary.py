from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import models
from ..utils import r_bridge
import openai
import json
import os

from ..utils.auth import get_current_user
from ..utils.ocr_service import ocr_service
import google.generativeai as genai # This is the old one, I should use the one I set up in ocr_service

# Actually, I'll use the gemini_client from ocr_service if possible, 
# or just initialize a new model here using the same SDK logic.

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
            "diagnoses": r.diagnoses,
            "medicines": r.medicines
        })
    
    # 2. Use Gemini for natural language summary across all history
    prompt = f"""
    You are a medical health assistant. Summarize the following medical history for the patient {current_user.name}.
    Focus on trends, recurring medications, and provide a friendly, encouraging health overview.
    Medical History:
    {json.dumps(records_context)}
    
    Keep the summary concise but informative. Format with bullet points if needed.
    """
    
    try:
        # Use a model from the client in ocr_service if we can, or just use genai directly if configured
        if ocr_service.gemini_client:
            response = ocr_service.gemini_client.models.generate_content(
                model='gemini-2.0-flash',
                contents=[prompt]
            )
            ai_summary = response.text.strip()
        else:
            ai_summary = "AI Summary Service is currently offline (Gemini not configured). However, your records are safely stored."
            
    except Exception as e:
        ai_summary = f"Summary generation paused: {str(e)}"

    return {
        "ai_summary": ai_summary,
        "record_count": len(records)
    }
