"""Hospital profile and action routes."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database.database import get_db
from app.models.hospital import Hospital
from app.models.user import User
from app.models.donor import Donor
from app.schemas.hospital_schema import HospitalCreate, HospitalUpdate, HospitalResponse
from app.schemas.donor_schema import DonorResponse
from app.auth.auth_dependencies import get_current_user, get_current_hospital
from app.utils.geo import calculate_distance

router = APIRouter(
    prefix="/hospital",
    tags=["Hospital"]
)


@router.post("/profile", response_model=HospitalResponse, status_code=status.HTTP_201_CREATED)
def create_hospital_profile(
    hospital_data: HospitalCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new hospital profile for the logged in user.
    """
    if current_user.role != "hospital":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User role must be 'hospital' to create a hospital profile."
        )

    # Check if profile already exists
    existing = db.query(Hospital).filter(Hospital.user_id == current_user.id).first()
    if existing:
        for key, value in hospital_data.model_dump(exclude_unset=True).items():
            setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing

    db_hospital = Hospital(
        user_id=current_user.id,
        name=hospital_data.name,
        city=hospital_data.city,
        address=hospital_data.address,
        contact_email=hospital_data.contact_email,
        phone=hospital_data.phone,
        latitude=hospital_data.latitude,
        longitude=hospital_data.longitude
    )
    db.add(db_hospital)
    db.commit()
    db.refresh(db_hospital)
    return db_hospital


@router.get("/profile", response_model=HospitalResponse)
def get_hospital_profile(
    current_hospital: Hospital = Depends(get_current_hospital)
):
    """
    Get current hospital's profile.
    """
    return current_hospital


@router.put("/profile", response_model=HospitalResponse)
def update_hospital_profile(
    hospital_data: HospitalUpdate,
    current_hospital: Hospital = Depends(get_current_hospital),
    db: Session = Depends(get_db)
):
    """
    Update hospital's profile.
    """
    for key, value in hospital_data.model_dump(exclude_unset=True).items():
        setattr(current_hospital, key, value)

    db.commit()
    db.refresh(current_hospital)
    return current_hospital


@router.get("/donors", response_model=List[DonorResponse])
def search_donors(
    blood_group: Optional[str] = Query(None, description="Filter by blood group"),
    city: Optional[str] = Query(None, description="Filter by city"),
    only_available: bool = Query(True, description="Filter only available donors"),
    radius_km: Optional[float] = Query(None, description="Search radius around hospital in km"),
    current_hospital: Hospital = Depends(get_current_hospital),
    db: Session = Depends(get_db)
):
    """
    Search and filter donors. If radius is provided, filters by coordinates relative to hospital.
    """
    query = db.query(Donor)

    if only_available:
        query = query.filter(Donor.is_available == True)

    if blood_group:
        blood_group = blood_group.strip().upper().replace(" ", "+")
        query = query.filter(Donor.blood_group == blood_group)

    if city:
        query = query.filter(Donor.city.ilike(f"%{city}%"))

    donors = query.all()

    # Filter by radius if requested
    if radius_km is not None:
        if current_hospital.latitude is None or current_hospital.longitude is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Hospital location coordinates must be set to run a radius search."
            )
        filtered = []
        for donor in donors:
            if donor.latitude is not None and donor.longitude is not None:
                dist = calculate_distance(
                    current_hospital.latitude,
                    current_hospital.longitude,
                    donor.latitude,
                    donor.longitude
                )
                if dist <= radius_km:
                    filtered.append(donor)
        return filtered

    return donors


@router.get("/donors/recommend")
def recommend_donors(
    blood_group: str = Query(..., description="Required blood group of recipient"),
    latitude: float = Query(..., description="Recipient/Hospital latitude"),
    longitude: float = Query(..., description="Recipient/Hospital longitude"),
    radius_km: float = Query(25.0, description="Max search radius in km"),
    top_n: int = Query(5, description="Number of recommendations to return"),
    current_hospital: Hospital = Depends(get_current_hospital),
    db: Session = Depends(get_db)
):
    """
    Recommend and rank compatible eligible donors using AI scoring (distance, availability, compatibility, response probability).
    """
    from app.ai.matcher import rank_donors
    normalized_blood_group = blood_group.strip().upper().replace(" ", "+")
    ranked = rank_donors(
        db=db,
        patient_blood_group=normalized_blood_group,
        target_lat=latitude,
        target_lon=longitude,
        max_radius_km=radius_km,
        top_n=top_n
    )
    return ranked


@router.post("/requests/{request_id}/broadcast-matching-donors")
def broadcast_matching_donors(
    request_id: int,
    radius_km: float = Query(25.0),
    top_n: int = Query(10),
    current_hospital: Hospital = Depends(get_current_hospital),
    db: Session = Depends(get_db)
):
    """
    Select top N matched donors and send them push notifications.
    """
    from app.ai.matcher import rank_donors
    from app.notifications.firebase import dispatch_notification
    from app.models.blood_request import BloodRequest

    req = db.query(BloodRequest).filter(BloodRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Blood request not found.")

    # Get target coordinates
    lat = req.latitude or current_hospital.latitude
    lon = req.longitude or current_hospital.longitude

    if lat is None or lon is None:
        raise HTTPException(status_code=400, detail="Blood request coordinates must be set.")

    # Run AI smart matching
    matched_donors = rank_donors(
        db=db,
        patient_blood_group=req.blood_group,
        target_lat=lat,
        target_lon=lon,
        max_radius_km=radius_km,
        top_n=top_n
    )

    dispatched = []
    for d in matched_donors:
        # Find donor object
        donor_obj = db.query(Donor).filter(Donor.id == d["donor_id"]).first()
        if donor_obj:
            # Construct push notification details
            title = "Urgent Blood Donation Request!"
            msg = f"A patient near you requires compatible {req.blood_group} blood. Tap to accept."
            
            res = dispatch_notification(
                db=db,
                user_id=donor_obj.user_id,
                title=title,
                message=msg,
                notification_type="emergency"
            )
            dispatched.append({
                "donor_id": donor_obj.id,
                "name": d["name"],
                "notification_id": res["notification_id"],
                "push_status": res["push_status"]
            })

    return {"detail": f"Notifications sent to {len(dispatched)} matching donors.", "recipients": dispatched}


@router.post("/broadcast-matching-donors")
def broadcast_matching_donors_general(
    blood_group: str = Query(...),
    radius_km: float = Query(25.0),
    latitude: float = Query(13.0827),
    longitude: float = Query(80.2707),
    current_hospital: Hospital = Depends(get_current_hospital),
    db: Session = Depends(get_db)
):
    """
    Broadcast notification to all matched compatible donors in radius.
    """
    from app.ai.matcher import rank_donors
    from app.notifications.firebase import dispatch_notification

    # Run AI smart matching
    normalized_blood_group = blood_group.strip().upper().replace(" ", "+")
    matched_donors = rank_donors(
        db=db,
        patient_blood_group=normalized_blood_group,
        target_lat=latitude,
        target_lon=longitude,
        max_radius_km=radius_km,
        top_n=10
    )

    dispatched = []
    for d in matched_donors:
        donor_obj = db.query(Donor).filter(Donor.id == d["donor_id"]).first()
        if donor_obj:
            title = f"Urgent {blood_group} Blood Request!"
            msg = f"A hospital near you requires compatible {blood_group} blood. Tap to accept."
            
            res = dispatch_notification(
                db=db,
                user_id=donor_obj.user_id,
                title=title,
                message=msg,
                notification_type="emergency"
            )
            dispatched.append({
                "donor_id": donor_obj.id,
                "name": d["name"],
                "push_status": res["push_status"]
            })

    return {"detail": f"Notifications sent to {len(dispatched)} matching donors.", "recipients": dispatched}



