"""Donor model."""

from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import relationship
from app.database.base import Base


class Donor(Base):
    __tablename__ = "donors"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    blood_group = Column(String, nullable=False, index=True)
    phone = Column(String)
    age = Column(Integer)
    gender = Column(String)
    address = Column(String)
    city = Column(String, index=True)
    latitude = Column(Float)
    longitude = Column(Float)
    is_available = Column(Boolean, default=True, index=True)
    last_donation_date = Column(DateTime(timezone=True), nullable=True)
    donation_count = Column(Integer, default=0)
    health_status = Column(String, default="Healthy")

    user = relationship("User", back_populates="donor")
    donations = relationship("Donation", back_populates="donor", cascade="all, delete-orphan")