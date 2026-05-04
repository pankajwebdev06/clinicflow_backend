from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ConsultationBase(BaseModel):
    clinic_id: str
    patient_id: str
    doctor_id: str
    doctor_notes: Optional[str] = None
    chief_complaints: Optional[str] = None
    diagnosis: Optional[str] = None
    handwritten_prescription_url: Optional[str] = None
    reports: Optional[str] = None

class ConsultationCreate(ConsultationBase):
    pass

class ConsultationUpdate(BaseModel):
    doctor_notes: Optional[str] = None
    chief_complaints: Optional[str] = None
    diagnosis: Optional[str] = None
    handwritten_prescription_url: Optional[str] = None
    reports: Optional[str] = None

class ConsultationResponse(ConsultationBase):
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
