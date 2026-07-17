from pydantic import BaseModel, ConfigDict
from typing import Optional


class PatientBase(BaseModel):
    blood_group: str
    city: str
    phone: Optional[str] = None
    address: Optional[str] = None
    medical_need: Optional[str] = None


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    blood_group: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    medical_need: Optional[str] = None


class PatientResponse(PatientBase):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)
