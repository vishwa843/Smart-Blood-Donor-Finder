"""Donation logging and verification routes."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import List

from app.database.database import get_db
from app.models.donation import Donation
from app.models.donor import Donor
from app.models.blood_request import BloodRequest
from app.models.hospital import Hospital
from app.models.user import User
from app.schemas.donation_schema import DonationCreate, DonationVerify, DonationResponse
from app.auth.auth_dependencies import get_current_user, get_current_donor, get_current_hospital

router = APIRouter(
    prefix="/donations",
    tags=["Donation"]
)


@router.post("/record", response_model=DonationResponse, status_code=status.HTTP_201_CREATED)
def record_donation(
    data: DonationCreate,
    current_donor: Donor = Depends(get_current_donor),
    db: Session = Depends(get_db)
):
    """
    Record a new donation event. A donor registers their intent/action of donating for an active blood request.
    This changes the request's status to 'accepted'.
    """
    # Fetch blood request
    req = db.query(BloodRequest).filter(BloodRequest.id == data.request_id).first()
    if not req:
        raise HTTPException(
            status_code=404,
            detail="Blood request not found."
        )

    if req.status not in ["pending", "accepted"]:
        raise HTTPException(
            status_code=400,
            detail=f"Blood request is already {req.status}."
        )

    # Check for duplicate pending donation by this donor
    dup = db.query(Donation).filter(
        Donation.donor_id == current_donor.id,
        Donation.request_id == req.id,
        Donation.status == "pending"
    ).first()
    if dup:
        return dup

    # Record donation
    donation = Donation(
        donor_id=current_donor.id,
        request_id=req.id,
        status="completed",
        certificate_code=f"CERT-{uuid.uuid4().hex[:12].upper()}",
        comments=data.comments
    )
    db.add(donation)

    # Set request status
    req.status = "accepted"

    # Update donor stats immediately
    current_donor.donation_count += 1
    current_donor.last_donation_date = func.now()

    db.commit()
    db.refresh(donation)
    return donation


@router.post("/{id}/verify", response_model=DonationResponse)
def verify_donation(
    id: int,
    verification: DonationVerify,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verify a donation. Usually invoked by the hospital associated with the request or an admin.
    Increments donor donation count, updates last donation date, generates certificate code,
    and sets request status to 'completed'.
    """
    donation = db.query(Donation).filter(Donation.id == id).first()
    if not donation:
        raise HTTPException(
            status_code=404,
            detail="Donation record not found."
        )

    if donation.status != "pending":
        raise HTTPException(
            status_code=400,
            detail="Donation is already processed."
        )

    # Fetch request
    req = db.query(BloodRequest).filter(BloodRequest.id == donation.request_id).first()
    if not req:
        raise HTTPException(
            status_code=404,
            detail="Associated blood request not found."
        )

    # Authorization check: must be the hospital for the request, or admin
    authorized = False
    if current_user.role == "admin":
        authorized = True
    elif current_user.role == "hospital":
        hospital = db.query(Hospital).filter(Hospital.user_id == current_user.id).first()
        if hospital and req.hospital_id == hospital.id:
            authorized = True

    if not authorized:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to verify this donation."
        )

    # Apply verification updates
    donation.status = verification.status
    if verification.comments:
        donation.comments = verification.comments

    # Generate certificate if completed
    if verification.status == "completed":
        donation.certificate_code = f"CERT-{uuid.uuid4().hex[:12].upper()}"

        # Update donor stats
        donor = db.query(Donor).filter(Donor.id == donation.donor_id).first()
        if donor:
            donor.donation_count += 1
            donor.last_donation_date = func.now()

        # Mark request as completed
        req.status = "completed"

    db.commit()
    db.refresh(donation)
    return donation


@router.get("/certificate/{id}")
def get_donation_certificate(
    id: int,
    db: Session = Depends(get_db)
):
    """
    Retrieve certificate verification details for a completed donation.
    """
    donation = db.query(Donation).filter(Donation.id == id).first()
    if not donation:
        raise HTTPException(
            status_code=404,
            detail="Donation record not found."
        )

    if donation.status != "completed" or not donation.certificate_code:
        raise HTTPException(
            status_code=400,
            detail="No certificate generated for this donation."
        )

    donor = db.query(Donor).filter(Donor.id == donation.donor_id).first()
    donor_user = db.query(User).filter(User.id == donor.user_id).first() if donor else None
    req = db.query(BloodRequest).filter(BloodRequest.id == donation.request_id).first()
    hospital = db.query(Hospital).filter(Hospital.id == req.hospital_id).first() if req and req.hospital_id else None

    return {
        "certificate_code": donation.certificate_code,
        "donor_name": donor_user.full_name if donor_user else "Anonymous",
        "blood_group": donor.blood_group if donor else "Unknown",
        "date_of_donation": donation.donated_at,
        "hospital_name": hospital.name if hospital else "Emergency Blood Finder Network",
        "status": "VERIFIED & VALID"
    }
