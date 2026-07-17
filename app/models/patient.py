"""Patient model."""

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.database.base import Base


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    blood_group = Column(String, nullable=False, index=True)
    city = Column(String, nullable=False, index=True)
    phone = Column(String)
    address = Column(String)
    medical_need = Column(String, nullable=True)

    user = relationship("User", back_populates="patient")
    blood_requests = relationship("BloodRequest", back_populates="patient", cascade="all, delete-orphan")

