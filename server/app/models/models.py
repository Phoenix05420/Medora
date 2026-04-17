from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, JSON, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String, default="patient") # patient, hospital, admin
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    name = Column(String)
    age = Column(Integer)
    gender = Column(String)
    blood_group = Column(String)
    location = Column(String)
    emergency_contact = Column(String)
    emergency_relation = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    records = relationship("MedicalRecord", back_populates="user")
    reminders = relationship("Reminder", back_populates="user")

class MedicalRecord(Base):
    __tablename__ = "medical_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    doctor_name = Column(String)
    visit_date = Column(Date)
    medicines = Column(JSON)  # List of {name, dosage, duration, frequency, route, validated}
    diagnoses = Column(JSON)  # List of condition strings
    raw_text = Column(String)
    notes = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="records")

class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    medicine_name = Column(String)
    dosage = Column(String)
    start_date = Column(Date)
    end_date = Column(Date)
    frequency = Column(String) # e.g., "Daily", "Twice a day"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="reminders")

class HospitalProfile(Base):
    __tablename__ = "hospital_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    specializations = Column(JSON) # e.g., ["cardio", "multispecialist"]
    lat = Column(String)
    lng = Column(String)
    address = Column(String)

    user = relationship("User")

class EmergencyAlert(Base):
    __tablename__ = "emergency_alerts"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"))
    hospital_id = Column(Integer, ForeignKey("users.id"))
    category = Column(String) # road accident, heart pain, etc.
    lat = Column(String)
    lng = Column(String)
    status = Column(String, default="pending") # pending, accepted, resolved
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"))
    hospital_id = Column(Integer, ForeignKey("users.id"))
    appointment_date = Column(DateTime(timezone=True))
    status = Column(String, default="scheduled")
    notes = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
