"""Blood request routes."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database.database import get_db
from app.models.blood_request import BloodRequest
from app.models.patient import Patient
from app.models.hospital import Hospital
from app.models.user import User
from app.schemas.blood_request_schema import BloodRequestCreate, BloodRequestUpdate, BloodRequestResponse
from app.auth.auth_dependencies import get_current_user
from app.utils.geo import calculate_distance

router = APIRouter(
    prefix="/blood-requests",
    tags=["Blood Request"]
)


@router.post("/", response_model=BloodRequestResponse, status_code=status.HTTP_201_CREATED)
def create_blood_request(
    data: BloodRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new blood request.
    If logged in as a patient, patient_id is automatically associated.
    If logged in as a hospital, hospital_id is automatically associated.
    """
    resolved_patient_id = data.patient_id
    resolved_hospital_id = data.hospital_id

    if current_user.role == "patient":
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient:
            raise HTTPException(
                status_code=400,
                detail="Complete patient profile before posting requests."
            )
        resolved_patient_id = patient.id
        resolved_hospital_id = None
    elif current_user.role == "hospital":
        hospital = db.query(Hospital).filter(Hospital.user_id == current_user.id).first()
        if not hospital:
            raise HTTPException(
                status_code=400,
                detail="Complete hospital profile before posting requests."
            )
        resolved_hospital_id = hospital.id
        if not resolved_patient_id:
            # Fallback or create dummy patient record if needed, but we require a patient_id.
            # For simplicity, if patient_id is empty, search if there is a default hospital-patient
            # or raise an error asking to specify the patient.
            # Let's see: we can create a default patient record linked to the hospital's email/phone,
            # or just require a patient_id. Let's raise an error if patient_id is missing for hospital.
            raise HTTPException(
                status_code=400,
                detail="A valid patient ID must be specified for hospital blood requests."
            )
    elif current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized to create blood requests."
        )

    # Double check patient exists
    patient_exists = db.query(Patient).filter(Patient.id == resolved_patient_id).first()
    if not patient_exists:
        raise HTTPException(
            status_code=404,
            detail="Patient not found."
        )

    # Verify hospital exists if provided
    if resolved_hospital_id:
        hospital_exists = db.query(Hospital).filter(Hospital.id == resolved_hospital_id).first()
        if not hospital_exists:
            raise HTTPException(
                status_code=404,
                detail="Hospital not found."
            )

    # Normalize blood group
    normalized_bg = data.blood_group.strip().upper().replace(" ", "+")

    # Create blood request
    req = BloodRequest(
        patient_id=resolved_patient_id,
        hospital_id=resolved_hospital_id,
        blood_group=normalized_bg,
        units_needed=data.units_needed,
        latitude=data.latitude,
        longitude=data.longitude,
        emergency_level=data.emergency_level,
        description=data.description,
        status="pending"
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    # Dispatch notifications to nearby hospitals and compatible donors
    from app.notifications.firebase import dispatch_notification
    from app.ai.matcher import rank_donors
    from app.models.donor import Donor

    if req.latitude is not None and req.longitude is not None:
        # 1. Find and notify all hospitals within 25km
        hospitals = db.query(Hospital).all()
        for hospital in hospitals:
            # Avoid notifying the hospital that created the request
            if resolved_hospital_id and hospital.id == resolved_hospital_id:
                continue
            if hospital.latitude is not None and hospital.longitude is not None:
                dist = calculate_distance(req.latitude, req.longitude, hospital.latitude, hospital.longitude)
                if dist <= 25.0:
                    dispatch_notification(
                        db=db,
                        user_id=hospital.user_id,
                        title="New Nearby Blood Request",
                        message=f"A patient requires {req.blood_group} blood within 25km. Request ID: #{req.id}.",
                        notification_type="info",
                        request_id=req.id
                    )

        # 2. Find and notify all compatible, available, healthy donors within 25km
        matched_donors = rank_donors(
            db=db,
            patient_blood_group=req.blood_group,
            target_lat=req.latitude,
            target_lon=req.longitude,
            max_radius_km=25.0,
            top_n=20
        )
        for d in matched_donors:
            donor_obj = db.query(Donor).filter(Donor.id == d["donor_id"]).first()
            if donor_obj:
                dispatch_notification(
                    db=db,
                    user_id=donor_obj.user_id,
                    title="Urgent Blood Request Nearby",
                    message=f"A request for compatible {req.blood_group} blood has been posted near you. Tap to accept.",
                    notification_type="emergency",
                    request_id=req.id
                )

    return req


@router.get("/", response_model=List[BloodRequestResponse])
def list_blood_requests(
    blood_group: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    List all blood requests with optional filters.
    """
    query = db.query(BloodRequest)

    if status:
        query = query.filter(BloodRequest.status == status)
    if blood_group:
        blood_group = blood_group.strip().upper().replace(" ", "+")
        query = query.filter(BloodRequest.blood_group == blood_group)

    requests = query.all()

    # Filter by city (needs checking patient's or hospital's city)
    if city:
        filtered = []
        for req in requests:
            # Check patient's city
            patient = db.query(Patient).filter(Patient.id == req.patient_id).first()
            if patient and city.lower() in patient.city.lower():
                filtered.append(req)
                continue
            # Check hospital's city
            if req.hospital_id:
                hospital = db.query(Hospital).filter(Hospital.id == req.hospital_id).first()
                if hospital and city.lower() in hospital.city.lower():
                    filtered.append(req)
        return filtered

    return requests


@router.get("/{id}", response_model=BloodRequestResponse)
def get_blood_request(
    id: int,
    db: Session = Depends(get_db)
):
    """
    Get a single blood request by ID.
    """
    req = db.query(BloodRequest).filter(BloodRequest.id == id).first()
    if not req:
        raise HTTPException(
            status_code=404,
            detail="Blood request not found."
        )
    return req


@router.put("/{id}", response_model=BloodRequestResponse)
def update_blood_request(
    id: int,
    data: BloodRequestUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a blood request.
    Authorized for the patient who created it, hospital associated, or admin.
    """
    req = db.query(BloodRequest).filter(BloodRequest.id == id).first()
    if not req:
        raise HTTPException(
            status_code=404,
            detail="Blood request not found."
        )

    # Permission check
    is_owner = False
    if current_user.role == "patient":
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if patient and req.patient_id == patient.id:
            is_owner = True
    elif current_user.role == "hospital":
        hospital = db.query(Hospital).filter(Hospital.user_id == current_user.id).first()
        if hospital and req.hospital_id == hospital.id:
            is_owner = True
    elif current_user.role == "admin":
        is_owner = True

    if not is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to edit this blood request."
        )

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(req, key, value)

    db.commit()
    db.refresh(req)
    return req


@router.get("/nearby/search", response_model=List[BloodRequestResponse])
def search_nearby_blood_requests(
    latitude: float,
    longitude: float,
    radius_km: float = Query(25.0),
    db: Session = Depends(get_db)
):
    """
    Search all active (pending) blood requests within a specified radius of arbitrary coordinates.
    """
    reqs = db.query(BloodRequest).filter(BloodRequest.status == "pending").all()
    nearby = []
    for req in reqs:
        if req.latitude is not None and req.longitude is not None:
            dist = calculate_distance(latitude, longitude, req.latitude, req.longitude)
            if dist <= radius_km:
                nearby.append(req)
    return nearby
