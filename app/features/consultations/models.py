from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime
import uuid

class Consultation(Base):
    __tablename__ = "consultations"

    id = Column(String, primary_key=True, index=True)
    clinic_id = Column(String, nullable=False, index=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(String, nullable=False) # ID of the doctor who provided the consultation
    
    # Priority: Doctor's Notes
    doctor_notes = Column(Text, nullable=True) # General notes
    chief_complaints = Column(Text, nullable=True)
    diagnosis = Column(Text, nullable=True)
    
    # Image/Document Storage (Supabase URLs)
    handwritten_prescription_url = Column(String, nullable=True)
    reports = Column(Text, nullable=True) # JSON string of list of report URLs
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    patient = relationship("Patient", back_populates="consultations")
