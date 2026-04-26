from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class QueueEntryCreate(BaseModel):
    clinic_id: str = Field(..., description="Clinic identifier")
    patient_id: str = Field(..., description="Patient identifier")
    priority: int = Field(0, ge=0, description="Priority (0=normal, higher=urgent)")
    symptoms: Optional[str] = None
    bp: Optional[str] = None
    weight: Optional[str] = None
    temperature: Optional[str] = None
    pulse: Optional[str] = None


class QueueEntryUpdate(BaseModel):
    status: Optional[str] = Field(None, description="waiting | in_consultation | completed | skipped | cancelled")
    priority: Optional[int] = Field(None, ge=0)


class QueueEntryResponse(BaseModel):
    id: str
    clinic_id: str
    patient_id: str
    token_number: str
    status: str
    priority: int
    symptoms: Optional[str] = None
    bp: Optional[str] = None
    weight: Optional[str] = None
    temperature: Optional[str] = None
    pulse: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
