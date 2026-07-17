"""Blood request model."""

from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.base import Base


class BloodRequest(Base):
    __tablename__ = "blood_requests"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=True)
    blood_group = Column(String, nullable=False, index=True)
    units_needed = Column(Integer, default=1)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    emergency_level = Column(String, default="normal")  # normal, urgent, critical
    description = Column(String, nullable=True)
    status = Column(String, default="pending", index=True)  # pending, accepted, completed, cancelled
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    patient = relationship("Patient", back_populates="blood_requests")
    hospital = relationship("Hospital", back_populates="blood_requests")
    donations = relationship("Donation", back_populates="blood_request", cascade="all, delete-orphan")

