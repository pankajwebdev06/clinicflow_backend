from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


# ── Medicine inside a prescription ──────────────────────
class MedicineCreate(BaseModel):
    medicine_name: str = Field(..., min_length=1, max_length=200)
    dosage: Optional[str] = None          # "500mg"
    frequency: Optional[str] = None       # "1-0-1"
    duration: Optional[str] = None        # "5 days"
    timing: Optional[str] = None          # "After food"
    quantity: Optional[int] = None
    instructions: Optional[str] = None


class MedicineResponse(MedicineCreate):
    id: str

    class Config:
        from_attributes = True


# ── Prescription ────────────────────────────────────────
class PrescriptionCreate(BaseModel):
    clinic_id: str
    patient_id: str
    doctor_id: str
    consultation_id: Optional[str] = None
    diagnosis: Optional[str] = None
    notes: Optional[str] = None
    medicines: List[MedicineCreate] = Field(default_factory=list)


class PrescriptionUpdate(BaseModel):
    diagnosis: Optional[str] = None
    notes: Optional[str] = None
    medicines: Optional[List[MedicineCreate]] = None  # Replaces all medicines if provided


class PrescriptionResponse(BaseModel):
    id: str
    clinic_id: str
    patient_id: str
    doctor_id: str
    consultation_id: Optional[str] = None
    diagnosis: Optional[str] = None
    notes: Optional[str] = None
    medicines: List[MedicineResponse] = []
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
