from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.features.auth.models import User
from app.features.patients.models import Patient
from app.features.patients.schemas import PatientCreate, PatientResponse

router = APIRouter()


@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    patient_data: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("doctor", "receptionist")),
):
    """Create a new patient. Accessible by doctor or receptionist."""
    # Check if patient exists
    existing = db.query(Patient).filter(
        Patient.clinic_id == patient_data.clinic_id,
        Patient.mobile_number == patient_data.mobile_number
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Patient already exists for this clinic")

    # Create new patient
    new_patient = Patient(
        id=str(uuid.uuid4()),
        **patient_data.model_dump()
    )
    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)
    return new_patient


@router.get("/", response_model=List[PatientResponse])
async def get_patients(
    clinic_id: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("doctor", "receptionist")),
):
    """List all patients for a clinic. Accessible by doctor or receptionist."""
    patients = db.query(Patient).filter(Patient.clinic_id == clinic_id).offset(skip).limit(limit).all()
    return patients
