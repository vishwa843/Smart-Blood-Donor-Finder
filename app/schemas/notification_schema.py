from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class NotificationBase(BaseModel):
    title: Optional[str] = None
    message: str
    type: str = "info"  # info, emergency, donation
    is_read: bool = False
    request_id: Optional[int] = None


class NotificationCreate(BaseModel):
    user_id: int
    title: Optional[str] = None
    message: str
    type: str = "info"


class NotificationResponse(NotificationBase):
    id: int
    user_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
