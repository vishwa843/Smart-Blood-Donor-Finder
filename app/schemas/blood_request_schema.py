from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class BloodRequestBase(BaseModel):
    blood_group: str
    units_needed: int = 1
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    emergency_level: str = "normal"  # normal, urgent, critical
    description: Optional[str] = None
    status: str = "pending"


class BloodRequestCreate(BaseModel):
    blood_group: str
    units_needed: int = 1
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    emergency_level: str = "normal"
    description: Optional[str] = None
    patient_id: Optional[int] = None  # Admin/Hospital can set this explicitly
    hospital_id: Optional[int] = None  # Admin can set this explicitly


class BloodRequestUpdate(BaseModel):
    blood_group: Optional[str] = None
    units_needed: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    emergency_level: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class BloodRequestResponse(BloodRequestBase):
    id: int
    patient_id: int
    hospital_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
