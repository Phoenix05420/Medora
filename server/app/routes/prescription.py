from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import models
from ..utils.ocr_service import ocr_service
import shutil
import os
import re
import logging
from typing import List

logger = logging.getLogger("ocr_service")

from ..utils.auth import get_current_user
from datetime import datetime

router = APIRouter(prefix="/prescriptions", tags=["prescriptions"])

# Ensure reports directory exists
REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

@router.get("/")
async def get_records(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Fetch all medical records for the current user."""
    records = db.query(models.MedicalRecord).filter(
        models.MedicalRecord.user_id == current_user.id
    ).order_by(models.MedicalRecord.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "doctor_name": r.doctor_name,
            "visit_date": str(r.visit_date) if r.visit_date else None,
            "medicines": r.medicines or [],
            "diagnoses": r.diagnoses or [],
            "raw_text": r.raw_text or "",
            "notes": r.notes or "",
            "created_at": str(r.created_at) if r.created_at else None,
        }
        for r in records
    ]

@router.get("/report/{record_id}")
async def download_report(record_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Download the PDF report for a specific record."""
    record = db.query(models.MedicalRecord).filter(
        models.MedicalRecord.id == record_id,
        models.MedicalRecord.user_id == current_user.id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    pdf_path = os.path.join(REPORTS_DIR, f"report_{record_id}.pdf")
    if os.path.exists(pdf_path):
        return FileResponse(pdf_path, media_type="application/pdf", filename=f"prescription_report_{record_id}.pdf")
    
    # Generate on-the-fly if missing
    ocr_data = {
        "doctor_name": record.doctor_name,
        "visit_date": str(record.visit_date) if record.visit_date else "Not detected",
        "medicines": record.medicines or [],
        "diagnoses": record.diagnoses or [],
        "raw_text": record.raw_text or "",
        "confidence": 0,
        "engines_used": ["Database"]
    }
    ocr_service.generate_pdf_report(ocr_data, pdf_path)
    return FileResponse(pdf_path, media_type="application/pdf", filename=f"prescription_report_{record_id}.pdf")

@router.post("/upload")
async def upload_prescription(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Process prescription image via triple-engine OCR, save to DB, and generate PDF report."""
    filename = f"user_{current_user.id}_{datetime.now().timestamp()}_{file.filename}"
    temp_path = os.path.join("temp", filename)
    os.makedirs("temp", exist_ok=True)
    
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Run triple-engine local OCR pipeline
        ocr_result = ocr_service.process_file(temp_path)
        
        # Parse visit date
        visit_date = None
        if ocr_result.get("visit_date"):
            try:
                for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
                    try:
                        visit_date = datetime.strptime(ocr_result["visit_date"], fmt).date()
                        break
                    except ValueError:
                        continue
            except Exception:
                visit_date = None

        # Save to database
        new_record = models.MedicalRecord(
            user_id=current_user.id,
            doctor_name=ocr_result.get("doctor_name", "Unknown"),
            visit_date=visit_date,
            medicines=ocr_result.get("medicines", []),
            diagnoses=ocr_result.get("diagnoses", []),
            raw_text=ocr_result.get("raw_text", ""),
            notes=f"Engines: {', '.join(ocr_result.get('engines_used', []))} | Confidence: {ocr_result.get('confidence', 0)}%"
        )
        
        db.add(new_record)
        db.commit()
        db.refresh(new_record)
        
        # Generate PDF report from the OCR JSON
        pdf_path = os.path.join(REPORTS_DIR, f"report_{new_record.id}.pdf")
        ocr_service.generate_pdf_report(ocr_result, pdf_path)
        
        return {
            "message": "Prescription processed and saved successfully",
            "record_id": new_record.id,
            "pdf_report": f"/prescriptions/report/{new_record.id}",
            "data": ocr_result
        }
    except Exception as e:
        db.rollback()
        logger.error(f"OCR Failure: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

