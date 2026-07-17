"""Donor profile and action routes."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List

from app.database.database import get_db
from app.models.donor import Donor
from app.models.user import User
from app.models.blood_request import BloodRequest
from app.models.donation import Donation
from app.schemas.donor_schema import DonorCreate, DonorUpdate, DonorResponse
from app.schemas.blood_request_schema import BloodRequestResponse
from app.schemas.donation_schema import DonationResponse
from app.auth.auth_dependencies import get_current_user, get_current_donor
from app.utils.geo import calculate_distance

router = APIRouter(
    prefix="/donor",
    tags=["Donor"]
)


@router.post("/profile", response_model=DonorResponse, status_code=status.HTTP_201_CREATED)
def create_donor_profile(
    donor_data: DonorCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new donor profile for the logged in user.
    """
    if current_user.role != "donor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User role must be 'donor' to create a donor profile."
        )

    # Check if profile already exists
    existing = db.query(Donor).filter(Donor.user_id == current_user.id).first()
    if existing:
        for key, value in donor_data.model_dump(exclude_unset=True).items():
            setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing

    db_donor = Donor(
        user_id=current_user.id,
        blood_group=donor_data.blood_group,
        phone=donor_data.phone,
        age=donor_data.age,
        gender=donor_data.gender,
        address=donor_data.address,
        city=donor_data.city,
        latitude=donor_data.latitude,
        longitude=donor_data.longitude,
        is_available=donor_data.is_available
    )
    db.add(db_donor)
    db.commit()
    db.refresh(db_donor)
    return db_donor


@router.get("/profile", response_model=DonorResponse)
def get_donor_profile(
    current_donor: Donor = Depends(get_current_donor)
):
    """
    Get current donor's profile.
    """
    return current_donor


@router.put("/profile", response_model=DonorResponse)
def update_donor_profile(
    donor_data: DonorUpdate,
    current_donor: Donor = Depends(get_current_donor),
    db: Session = Depends(get_db)
):
    """
    Update donor's profile.
    """
    for key, value in donor_data.model_dump(exclude_unset=True).items():
        setattr(current_donor, key, value)

    db.commit()
    db.refresh(current_donor)
    return current_donor


@router.put("/availability", response_model=DonorResponse)
def toggle_availability(
    is_available: bool,
    current_donor: Donor = Depends(get_current_donor),
    db: Session = Depends(get_db)
):
    """
    Toggle donor's availability status.
    """
    current_donor.is_available = is_available
    db.commit()
    db.refresh(current_donor)
    return current_donor


@router.get("/history", response_model=List[DonationResponse])
def get_donation_history(
    current_donor: Donor = Depends(get_current_donor),
    db: Session = Depends(get_db)
):
    """
    Get current donor's donation logs.
    """
    donations = db.query(Donation).filter(
        Donation.donor_id == current_donor.id
    ).all()
    return donations


@router.get("/requests/nearby", response_model=List[BloodRequestResponse])
def get_nearby_blood_requests(
    radius_km: float = Query(25.0, description="Search radius in kilometers"),
    current_donor: Donor = Depends(get_current_donor),
    db: Session = Depends(get_db)
):
    """
    Retrieve active (pending) blood requests within the specified radius of the donor's coordinates.
    Filters by matching blood group compatibility or all groups.
    """
    if current_donor.latitude is None or current_donor.longitude is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Donor location coordinates must be set to locate nearby requests."
        )

    # Fetch pending requests
    active_requests = db.query(BloodRequest).filter(
        BloodRequest.status == "pending"
    ).all()

    from app.ai.matcher import is_compatible

    nearby = []
    for req in active_requests:
        if req.latitude is not None and req.longitude is not None:
            dist = calculate_distance(
                current_donor.latitude,
                current_donor.longitude,
                req.latitude,
                req.longitude
            )
            if dist <= radius_km:
                if is_compatible(current_donor.blood_group, req.blood_group):
                    nearby.append(req)

    return nearby


@router.put("/requests/{request_id}/accept", response_model=BloodRequestResponse)
def accept_blood_request(
    request_id: int,
    current_donor: Donor = Depends(get_current_donor),
    db: Session = Depends(get_db)
):
    """
    Accept an active blood request. Updates status to 'accepted' and notifies hospital and patient.
    """
    from app.notifications.firebase import dispatch_notification
    from app.models.patient import Patient
    from app.models.hospital import Hospital

    req = db.query(BloodRequest).filter(BloodRequest.id == request_id).first()
    if not req:
        raise HTTPException(
            status_code=404,
            detail="Blood request not found."
        )

    if req.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"This blood request is already {req.status}."
        )

    req.status = "accepted"
    db.commit()
    db.refresh(req)

    # Fetch donor's user object for name
    donor_user = db.query(User).filter(User.id == current_donor.user_id).first()
    donor_name = donor_user.full_name if donor_user else "A compatible donor"

    # 1. Notify the patient
    patient = db.query(Patient).filter(Patient.id == req.patient_id).first()
    if patient:
        patient_title = "Blood Request Accepted!"
        patient_msg = f"{donor_name} has accepted your request for {req.blood_group} blood and is on the way."
        dispatch_notification(
            db=db,
            user_id=patient.user_id,
            title=patient_title,
            message=patient_msg,
            notification_type="info"
        )

    # 2. Notify the hospital if request is linked to one, otherwise notify nearby hospitals
    if req.hospital_id:
        hospital = db.query(Hospital).filter(Hospital.id == req.hospital_id).first()
        if hospital:
            hospital_title = "Donor Accepted Request"
            hospital_msg = f"{donor_name} has accepted Blood Request #{req.id} for {req.blood_group}."
            dispatch_notification(
                db=db,
                user_id=hospital.user_id,
                title=hospital_title,
                message=hospital_msg,
                notification_type="info"
            )
    else:
        if req.latitude is not None and req.longitude is not None:
            hospitals = db.query(Hospital).all()
            for hospital in hospitals:
                if hospital.latitude is not None and hospital.longitude is not None:
                    dist = calculate_distance(req.latitude, req.longitude, hospital.latitude, hospital.longitude)
                    if dist <= 25.0:
                        dispatch_notification(
                            db=db,
                            user_id=hospital.user_id,
                            title="Donor Accepted Nearby Request",
                            message=f"{donor_name} has accepted Blood Request #{req.id} for {req.blood_group} near your location.",
                            notification_type="info"
                        )

    return req


@router.put("/requests/{request_id}/on-the-way", response_model=BloodRequestResponse)
def donor_on_the_way(
    request_id: int,
    current_donor: Donor = Depends(get_current_donor),
    db: Session = Depends(get_db)
):
    """
    Donor has started traveling to the hospital or recipient. Updates request status to 'on_the_way'.
    """
    from app.notifications.firebase import dispatch_notification
    from app.models.patient import Patient
    from app.models.hospital import Hospital

    req = db.query(BloodRequest).filter(BloodRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Blood request not found.")

    if req.status != "accepted":
        raise HTTPException(status_code=400, detail="Blood request must be accepted first.")

    req.status = "on_the_way"
    db.commit()
    db.refresh(req)

    donor_user = db.query(User).filter(User.id == current_donor.user_id).first()
    donor_name = donor_user.full_name if donor_user else "The donor"

    # Notify patient
    patient = db.query(Patient).filter(Patient.id == req.patient_id).first()
    if patient:
        dispatch_notification(
            db=db,
            user_id=patient.user_id,
            title="Donor is on the way!",
            message=f"{donor_name} is on the way to complete your donation.",
            notification_type="info"
        )

    # Notify hospital
    if req.hospital_id:
        hospital = db.query(Hospital).filter(Hospital.id == req.hospital_id).first()
        if hospital:
            dispatch_notification(
                db=db,
                user_id=hospital.user_id,
                title="Donor on the way",
                message=f"{donor_name} is traveling to your facility for Request #{req.id}.",
                notification_type="info"
            )
    else:
        if req.latitude is not None and req.longitude is not None:
            hospitals = db.query(Hospital).all()
            for hospital in hospitals:
                if hospital.latitude is not None and hospital.longitude is not None:
                    dist = calculate_distance(req.latitude, req.longitude, hospital.latitude, hospital.longitude)
                    if dist <= 25.0:
                        dispatch_notification(
                            db=db,
                            user_id=hospital.user_id,
                            title="Donor on the way",
                            message=f"{donor_name} is traveling to perform donation for Request #{req.id}.",
                            notification_type="info"
                        )

    return req


@router.put("/requests/{request_id}/reject", response_model=BloodRequestResponse)
def donor_reject_request(
    request_id: int,
    current_donor: Donor = Depends(get_current_donor),
    db: Session = Depends(get_db)
):
    """
    Donor has rejected/cancelled their accepted status. Resets request status back to 'pending'.
    """
    from app.notifications.firebase import dispatch_notification
    from app.models.patient import Patient
    from app.models.hospital import Hospital
    from app.models.donation import Donation

    req = db.query(BloodRequest).filter(BloodRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Blood request not found.")

    if req.status not in ["accepted", "on_the_way"]:
        raise HTTPException(status_code=400, detail="Cannot cancel this request in its current state.")

    req.status = "pending"

    # Cancel associated donation logs
    donation = db.query(Donation).filter(
        Donation.request_id == req.id,
        Donation.donor_id == current_donor.id,
        Donation.status == "pending"
    ).first()
    if donation:
        donation.status = "cancelled"

    db.commit()
    db.refresh(req)

    donor_user = db.query(User).filter(User.id == current_donor.user_id).first()
    donor_name = donor_user.full_name if donor_user else "The donor"

    # Notify patient
    patient = db.query(Patient).filter(Patient.id == req.patient_id).first()
    if patient:
        dispatch_notification(
            db=db,
            user_id=patient.user_id,
            title="Donor Had to Cancel",
            message=f"{donor_name} had to cancel. Your request has been returned to the active finder list.",
            notification_type="warning"
        )

    # Notify hospital
    if req.hospital_id:
        hospital = db.query(Hospital).filter(Hospital.id == req.hospital_id).first()
        if hospital:
            dispatch_notification(
                db=db,
                user_id=hospital.user_id,
                title="Donor Cancelled",
                message=f"The assigned donor cancelled for Request #{req.id}. Rescheduling match search.",
                notification_type="warning"
            )
    else:
        if req.latitude is not None and req.longitude is not None:
            hospitals = db.query(Hospital).all()
            for hospital in hospitals:
                if hospital.latitude is not None and hospital.longitude is not None:
                    dist = calculate_distance(req.latitude, req.longitude, hospital.latitude, hospital.longitude)
                    if dist <= 25.0:
                        dispatch_notification(
                            db=db,
                            user_id=hospital.user_id,
                            title="Donor Cancelled",
                            message=f"The assigned donor cancelled for Request #{req.id} near your location.",
                            notification_type="warning"
                        )

    return req