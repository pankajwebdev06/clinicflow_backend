from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Float
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime


class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(String, primary_key=True, index=True)
    clinic_id = Column(String, nullable=False, index=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False)
    consultation_id = Column(String, ForeignKey("consultations.id"), nullable=True)
    doctor_id = Column(String, nullable=False)

    # Diagnosis summary (copied from consultation for print)
    diagnosis = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    medicines = relationship("PrescriptionMedicine", back_populates="prescription", cascade="all, delete-orphan")
    patient = relationship("Patient", back_populates="prescriptions")


class PrescriptionMedicine(Base):
    __tablename__ = "prescription_medicines"

    id = Column(String, primary_key=True, index=True)
    prescription_id = Column(String, ForeignKey("prescriptions.id"), nullable=False)

    medicine_name = Column(String(200), nullable=False)
    dosage = Column(String(100), nullable=True)       # e.g. "500mg"
    frequency = Column(String(100), nullable=True)     # e.g. "1-0-1" or "Twice daily"
    duration = Column(String(100), nullable=True)       # e.g. "5 days"
    timing = Column(String(50), nullable=True)          # e.g. "After food"
    quantity = Column(Integer, nullable=True)
    instructions = Column(Text, nullable=True)          # Special instructions

    # Relationship
    prescription = relationship("Prescription", back_populates="medicines")
