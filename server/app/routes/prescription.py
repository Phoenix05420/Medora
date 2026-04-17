from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import models
from ..utils.ocr_service import ocr_service
import shutil
import os
import re
from typing import List

from ..utils.auth import get_current_user
from datetime import datetime

router = APIRouter(prefix="/prescriptions", tags=["prescriptions"])

@router.get("/", response_model=List[dict])
async def get_records(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Fetch all medical records for the current user."""
    records = db.query(models.MedicalRecord).filter(
        models.MedicalRecord.user_id == current_user.id
    ).order_by(models.MedicalRecord.created_at.desc()).all()
    return records

@router.post("/upload")
async def upload_prescription(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Process prescription image, extract data, and save to database."""
    # Save the file temporarily
    filename = f"user_{current_user.id}_{datetime.now().timestamp()}_{file.filename}"
    temp_path = os.path.join("temp", filename)
    os.makedirs("temp", exist_ok=True)
    
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Use our hybrid OCR pipeline
        ocr_result = ocr_service.process_file(temp_path)
        
        # Parse visit date (string to date object)
        visit_date = None
        if ocr_result.get("visit_date"):
            try:
                # Try common formats
                for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
                    try:
                        visit_date = datetime.strptime(ocr_result["visit_date"], fmt).date()
                        break
                    except ValueError:
                        continue
            except Exception:
                visit_date = None

        # Create database record
        new_record = models.MedicalRecord(
            user_id=current_user.id,
            doctor_name=ocr_result.get("doctor_name", "Unknown"),
            visit_date=visit_date,
            medicines=ocr_result.get("medicines", []),
            diagnoses=ocr_result.get("diagnoses", []),
            raw_text=ocr_result.get("raw_text", ""),
            notes=f"Scanned with confidence: {ocr_result.get('confidence', 0)}%"
        )
        
        db.add(new_record)
        db.commit()
        db.refresh(new_record)
        
        return {
            "message": "Prescription processed and saved successfully",
            "record_id": new_record.id,
            "data": ocr_result
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"OCR processing or saving failed: {str(e)}")
    finally:
        # Clean up
        if os.path.exists(temp_path):
            os.remove(temp_path)
