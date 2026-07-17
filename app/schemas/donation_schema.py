from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class DonationBase(BaseModel):
    donor_id: int
    request_id: int
    status: str = "pending"  # pending, verified, completed, cancelled
    comments: Optional[str] = None


class DonationCreate(BaseModel):
    request_id: int
    comments: Optional[str] = None


class DonationVerify(BaseModel):
    status: str = "completed"
    comments: Optional[str] = None


class DonationResponse(DonationBase):
    id: int
    certificate_code: Optional[str] = None
    donated_at: datetime

    model_config = ConfigDict(from_attributes=True)
