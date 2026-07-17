"""Hospital model."""

from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.database.base import Base


class Hospital(Base):
    __tablename__ = "hospitals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False, index=True)
    city = Column(String, nullable=False, index=True)
    address = Column(String)
    contact_email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    latitude = Column(Float)
    longitude = Column(Float)
    is_approved = Column(Boolean, default=False)

    user = relationship("User", back_populates="hospital")
    blood_requests = relationship("BloodRequest", back_populates="hospital", cascade="all, delete-orphan")

