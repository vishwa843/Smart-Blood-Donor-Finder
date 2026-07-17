from pydantic import BaseModel, ConfigDict
from typing import Optional


class HospitalBase(BaseModel):
    name: str
    city: str
    address: Optional[str] = None
    contact_email: Optional[str] = None
    phone: Optional[str] = None
    latitude: float
    longitude: float


class HospitalCreate(HospitalBase):
    pass


class HospitalUpdate(BaseModel):
    name: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    contact_email: Optional[str] = None
    phone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class HospitalResponse(HospitalBase):
    id: int
    user_id: int
    is_approved: bool

    model_config = ConfigDict(from_attributes=True)
