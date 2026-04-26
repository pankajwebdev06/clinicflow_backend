from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid
from datetime import datetime

from app.core.database import get_db
from app.core.deps import require_role
from app.features.auth.models import User
from app.features.prescriptions.models import Prescription, PrescriptionMedicine
from app.features.prescriptions.schemas import (
    PrescriptionCreate, PrescriptionUpdate, PrescriptionResponse,
)

router = APIRouter()


# ── CREATE ──────────────────────────────────────────────
@router.post("/", response_model=PrescriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_prescription(
    data: PrescriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("doctor")),
):
    """Create a new prescription with medicines. Doctor only."""
    prescription = Prescription(
        id=str(uuid.uuid4()),
        clinic_id=data.clinic_id,
        patient_id=data.patient_id,
        doctor_id=data.doctor_id,
        consultation_id=data.consultation_id,
        diagnosis=data.diagnosis,
        notes=data.notes,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    for med in data.medicines:
        medicine = PrescriptionMedicine(
            id=str(uuid.uuid4()),
            prescription_id=prescription.id,
            **med.model_dump()
        )
        prescription.medicines.append(medicine)

    db.add(prescription)
    db.commit()
    db.refresh(prescription)
    return prescription


# ── GET by ID ───────────────────────────────────────────
@router.get("/{prescription_id}", response_model=PrescriptionResponse)
async def get_prescription(
    prescription_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("doctor", "receptionist")),
):
    """Get a prescription with all its medicines. Doctor or receptionist."""
    prescription = db.query(Prescription).filter(Prescription.id == prescription_id).first()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    return prescription


# ── GET all for a patient ───────────────────────────────
@router.get("/patient/{patient_id}", response_model=List[PrescriptionResponse])
async def get_patient_prescriptions(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("doctor", "receptionist")),
):
    """Get all prescriptions for a patient. Doctor or receptionist."""
    return db.query(Prescription).filter(
        Prescription.patient_id == patient_id
    ).order_by(Prescription.created_at.desc()).all()


# ── UPDATE ──────────────────────────────────────────────
@router.patch("/{prescription_id}", response_model=PrescriptionResponse)
async def update_prescription(
    prescription_id: str,
    data: PrescriptionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("doctor")),
):
    """Update prescription details or replace medicines list. Doctor only."""
    prescription = db.query(Prescription).filter(Prescription.id == prescription_id).first()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")

    if data.diagnosis is not None:
        prescription.diagnosis = data.diagnosis
    if data.notes is not None:
        prescription.notes = data.notes

    if data.medicines is not None:
        db.query(PrescriptionMedicine).filter(
            PrescriptionMedicine.prescription_id == prescription_id
        ).delete()

        for med in data.medicines:
            medicine = PrescriptionMedicine(
                id=str(uuid.uuid4()),
                prescription_id=prescription_id,
                **med.model_dump()
            )
            db.add(medicine)

    prescription.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(prescription)
    return prescription


# ── DELETE ──────────────────────────────────────────────
@router.delete("/{prescription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prescription(
    prescription_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("doctor")),
):
    """Delete a prescription and all its medicines. Doctor only."""
    prescription = db.query(Prescription).filter(Prescription.id == prescription_id).first()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")

    db.delete(prescription)
    db.commit()
