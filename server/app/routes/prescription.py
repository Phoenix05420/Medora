from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from ..database import get_db, SessionLocal
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
            "status": r.status or "completed",
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

def process_prescription_background(file_path: str, record_id: int):
    """Background task to process the OCR and update the database."""
    db = SessionLocal()
    try:
        # Run triple-engine local OCR pipeline
        ocr_result = ocr_service.process_file(file_path)
        
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

        # Fetch the pending record to update
        record = db.query(models.MedicalRecord).filter(models.MedicalRecord.id == record_id).first()
        if record:
            record.doctor_name = ocr_result.get("doctor_name", "Unknown")
            record.visit_date = visit_date
            record.medicines = ocr_result.get("medicines", [])
            record.diagnoses = ocr_result.get("diagnoses", [])
            record.raw_text = ocr_result.get("raw_text", "")
            record.notes = f"Engines: {', '.join(ocr_result.get('engines_used', []))} | Confidence: {ocr_result.get('confidence', 0)}%"
            record.status = "completed"
            
            db.commit()
            
            # Generate PDF report
            pdf_path = os.path.join(REPORTS_DIR, f"report_{record.id}.pdf")
            ocr_service.generate_pdf_report(ocr_result, pdf_path)
            
    except Exception as e:
        logger.error(f"Background OCR Failure: {str(e)}", exc_info=True)
        record = db.query(models.MedicalRecord).filter(models.MedicalRecord.id == record_id).first()
        if record:
            record.status = "failed"
            record.notes = f"Processing failed: {str(e)}"
            db.commit()
    finally:
        db.close()
        if os.path.exists(file_path):
            os.remove(file_path)

@router.post("/upload")
async def upload_prescription(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...), 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Start prescription processing asynchronously."""
    filename = f"user_{current_user.id}_{datetime.now().timestamp()}_{file.filename}"
    temp_path = os.path.join("temp", filename)
    os.makedirs("temp", exist_ok=True)
    
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Create an initial pending record in the database
        new_record = models.MedicalRecord(
            user_id=current_user.id,
            doctor_name="Processing AI Scan...",
            status="pending",
            medicines=[],
            diagnoses=[],
            raw_text="Extraction in progress..."
        )
        
        db.add(new_record)
        db.commit()
        db.refresh(new_record)
        
        # Dispatch the actual processing to the background
        background_tasks.add_task(process_prescription_background, temp_path, new_record.id)
        
        return {
            "message": "Prescription received and is processing in background",
            "record_id": new_record.id,
            "status": "pending"
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Upload Failure: {str(e)}", exc_info=True)
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

