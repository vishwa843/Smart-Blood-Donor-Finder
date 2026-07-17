"""Donation model."""

from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.base import Base


class Donation(Base):
    __tablename__ = "donations"

    id = Column(Integer, primary_key=True, index=True)
    donor_id = Column(Integer, ForeignKey("donors.id"), nullable=False)
    request_id = Column(Integer, ForeignKey("blood_requests.id"), nullable=False)
    status = Column(String, default="pending", index=True)  # pending, verified, completed, cancelled
    certificate_code = Column(String, unique=True, nullable=True)
    comments = Column(String, nullable=True)
    donated_at = Column(DateTime(timezone=True), server_default=func.now())

    donor = relationship("Donor", back_populates="donations")
    blood_request = relationship("BloodRequest", back_populates="donations")

