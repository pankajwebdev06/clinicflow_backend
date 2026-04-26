from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid

from app.core.database import get_db
from app.core.deps import require_role
from app.features.auth.models import User
from app.features.consultations.models import Consultation
from app.features.consultations.schemas import ConsultationCreate, ConsultationResponse, ConsultationUpdate

router = APIRouter()


@router.post("/", response_model=ConsultationResponse, status_code=status.HTTP_201_CREATED)
async def create_consultation(
    data: ConsultationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("doctor")),
):
    """Create a new consultation with doctor notes. Doctor only."""
    consultation = Consultation(
        id=str(uuid.uuid4()),
        **data.model_dump()
    )
    db.add(consultation)
    db.commit()
    db.refresh(consultation)
    return consultation


@router.get("/patient/{patient_id}", response_model=List[ConsultationResponse])
async def get_patient_history(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("doctor", "receptionist")),
):
    """Get all previous consultations for a patient. Doctor or receptionist."""
    history = db.query(Consultation).filter(
        Consultation.patient_id == patient_id
    ).order_by(Consultation.created_at.desc()).all()
    return history


@router.get("/{consultation_id}", response_model=ConsultationResponse)
async def get_consultation(
    consultation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("doctor")),
):
    """Get specific consultation details. Doctor only."""
    consultation = db.query(Consultation).filter(Consultation.id == consultation_id).first()
    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation not found")
    return consultation


@router.patch("/{consultation_id}", response_model=ConsultationResponse)
async def update_notes(
    consultation_id: str,
    data: ConsultationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("doctor")),
):
    """Update doctor's notes in a consultation. Doctor only."""
    consultation = db.query(Consultation).filter(Consultation.id == consultation_id).first()
    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(consultation, key, value)

    db.commit()
    db.refresh(consultation)
    return consultation
