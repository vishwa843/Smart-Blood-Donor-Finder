"""Patient profile and action routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database.database import get_db
from app.models.patient import Patient
from app.models.user import User
from app.models.blood_request import BloodRequest
from app.schemas.patient_schema import PatientCreate, PatientUpdate, PatientResponse
from app.schemas.blood_request_schema import BloodRequestResponse
from app.auth.auth_dependencies import get_current_user, get_current_patient

router = APIRouter(
    prefix="/patient",
    tags=["Patient"]
)


@router.post("/profile", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
def create_patient_profile(
    patient_data: PatientCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new patient profile for the logged in user.
    """
    if current_user.role != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User role must be 'patient' to create a patient profile."
        )

    # Check if profile already exists
    existing = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if existing:
        for key, value in patient_data.model_dump(exclude_unset=True).items():
            setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing

    db_patient = Patient(
        user_id=current_user.id,
        blood_group=patient_data.blood_group,
        city=patient_data.city,
        phone=patient_data.phone,
        address=patient_data.address,
        medical_need=patient_data.medical_need
    )
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return db_patient


@router.get("/profile", response_model=PatientResponse)
def get_patient_profile(
    current_patient: Patient = Depends(get_current_patient)
):
    """
    Get current patient's profile.
    """
    return current_patient


@router.put("/profile", response_model=PatientResponse)
def update_patient_profile(
    patient_data: PatientUpdate,
    current_patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db)
):
    """
    Update patient's profile.
    """
    for key, value in patient_data.model_dump(exclude_unset=True).items():
        setattr(current_patient, key, value)

    db.commit()
    db.refresh(current_patient)
    return current_patient


@router.get("/requests", response_model=List[BloodRequestResponse])
def get_patient_requests(
    current_patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db)
):
    """
    Get all blood requests created by this patient.
    """
    requests = db.query(BloodRequest).filter(
        BloodRequest.patient_id == current_patient.id
    ).all()
    return requests
