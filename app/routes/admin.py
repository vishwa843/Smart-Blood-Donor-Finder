"""Admin dashboard and management routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any

from app.database.database import get_db
from app.models.user import User
from app.models.donor import Donor
from app.models.patient import Patient
from app.models.hospital import Hospital
from app.models.blood_request import BloodRequest
from app.models.donation import Donation
from app.schemas.user_schema import UserResponse
from app.schemas.hospital_schema import HospitalResponse
from app.auth.auth_dependencies import get_current_admin

router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)


@router.get("/dashboard", response_model=Dict[str, Any])
def get_admin_dashboard_metrics(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Retrieve global system performance and entity counts.
    """
    total_users = db.query(User).count()
    total_donors = db.query(Donor).count()
    total_patients = db.query(Patient).count()
    total_hospitals = db.query(Hospital).count()
    total_requests = db.query(BloodRequest).count()
    total_donations = db.query(Donation).count()

    # Success rate logic
    completed_requests = db.query(BloodRequest).filter(BloodRequest.status == "completed").count()
    success_rate = (completed_requests / total_requests * 100.0) if total_requests > 0 else 0.0

    # Group requests by status
    status_counts = db.query(
        BloodRequest.status, func.count(BloodRequest.id)
    ).group_by(BloodRequest.status).all()
    status_map = {status: count for status, count in status_counts}

    return {
        "metrics": {
            "total_users": total_users,
            "total_donors": total_donors,
            "total_patients": total_patients,
            "total_hospitals": total_hospitals,
            "total_requests": total_requests,
            "total_donations": total_donations,
            "success_rate_percent": round(success_rate, 1)
        },
        "requests_by_status": status_map
    }


@router.get("/users", response_model=List[UserResponse])
def manage_users(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    List all users in the system.
    """
    return db.query(User).all()


@router.put("/users/{id}/deactivate", response_model=UserResponse)
def deactivate_user(
    id: int,
    is_active: bool,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Deactivate or activate a user account.
    """
    user = db.query(User).filter(User.id == id).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found."
        )
    user.is_active = is_active
    db.commit()
    db.refresh(user)
    return user


@router.put("/hospitals/{id}/approve", response_model=HospitalResponse)
def approve_hospital(
    id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Approve hospital credentials to enable blood requests and donor listings.
    """
    hospital = db.query(Hospital).filter(Hospital.id == id).first()
    if not hospital:
        raise HTTPException(
            status_code=404,
            detail="Hospital profile not found."
        )
    hospital.is_approved = True
    db.commit()
    db.refresh(hospital)
    return hospital
