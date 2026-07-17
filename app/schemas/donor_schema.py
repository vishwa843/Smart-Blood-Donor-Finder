from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class DonorBase(BaseModel):
    blood_group: str
    phone: str
    age: int
    gender: str
    address: str
    city: str
    latitude: float
    longitude: float
    is_available: bool = True
    health_status: str = "Healthy"


class DonorCreate(DonorBase):
    pass


class DonorUpdate(BaseModel):
    phone: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_available: Optional[bool] = None
    last_donation_date: Optional[datetime] = None
    health_status: Optional[str] = None


class DonorResponse(DonorBase):
    id: int
    user_id: int
    last_donation_date: Optional[datetime] = None
    donation_count: int = 0
    health_status: str

    model_config = ConfigDict(from_attributes=True)