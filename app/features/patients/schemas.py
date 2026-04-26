from pydantic import BaseModel, constr
from datetime import datetime
from typing import Optional
from app.features.patients.models import Gender

class PatientBase(BaseModel):
    clinic_id: str
    mobile_number: str
    name: str
    age: int
    gender: Gender

class PatientCreate(PatientBase):
    pass

class PatientResponse(PatientBase):
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
