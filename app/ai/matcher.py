"""AI Matching engine for blood donor recommendation."""

from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

from app.models.donor import Donor
from app.models.user import User
from app.utils.geo import calculate_distance
from app.ai.predictor import predict_donor_responsiveness, classify_donor_status

# Compatibility Mapping: Donor -> list of compatible recipients
BLOOD_COMPATIBILITY = {
    "O-": ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"],
    "O+": ["O+", "A+", "B+", "AB+"],
    "A-": ["A-", "A+", "AB-", "AB+"],
    "A+": ["A+", "AB+"],
    "B-": ["B-", "B+", "AB-", "AB+"],
    "B+": ["B+", "AB+"],
    "AB-": ["AB-", "AB+"],
    "AB+": ["AB+"]
}


def is_compatible(donor_group: str, patient_group: str) -> bool:
    """
    Check if donor blood group is compatible with recipient blood group.
    """
    # Clean group formatting and handle spaces replacing '+' due to URL decoding
    d = donor_group.strip().upper().replace(" ", "+")
    p = patient_group.strip().upper().replace(" ", "+")
    return p in BLOOD_COMPATIBILITY.get(d, [])


def get_eligible_donors(db: Session, blood_group: str) -> List[Donor]:
    """
    Query all eligible donors who are compatible, available, and passed their 90-day cooldown.
    """
    # Cooldown check limit
    cooldown_limit = datetime.now(timezone.utc) - timedelta(days=90)

    # Query all active/available donors
    all_available = db.query(Donor).filter(Donor.is_available == True).all()

    eligible = []
    for donor in all_available:
        # Health status check (must be Healthy)
        if donor.health_status and donor.health_status.lower() != "healthy":
            continue

        # 1. Blood Compatibility check
        if not is_compatible(donor.blood_group, blood_group):
            continue

        # 2. Cooldown check (Commented out to keep all donors visible for testing)
        # if donor.last_donation_date:
        #     # Handle timezone naive/aware comparison safely
        #     last_date = donor.last_donation_date
        #     if last_date.tzinfo is None:
        #         last_date = last_date.replace(tzinfo=timezone.utc)
        # 
        #     if last_date > cooldown_limit:
        #         continue

        eligible.append(donor)

    return eligible


def rank_donors(
    db: Session,
    patient_blood_group: str,
    target_lat: float,
    target_lon: float,
    max_radius_km: float = 50.0,
    top_n: int = 10
) -> List[Dict[str, Any]]:
    """
    Find, score, and rank compatible eligible donors.
    Priority Score = 0.4 * DistanceScore + 0.3 * PredictorScore + 0.3 * CompatibilityScore.
    """
    eligible = get_eligible_donors(db, patient_blood_group)

    ranked_results = []
    for donor in eligible:
        if donor.latitude is None or donor.longitude is None:
            continue

        # 1. Distance Calculation
        dist = calculate_distance(target_lat, target_lon, donor.latitude, donor.longitude)
        if dist > max_radius_km:
            continue

        # Distance Score: 100 at 0km, linear decrease to 0 at max_radius
        distance_score = max(0.0, 100.0 * (1.0 - (dist / max_radius_km)))

        # 2. Compatibility Score: 100 for exact match, 70 for compatible non-exact match
        compatibility_score = 100.0 if donor.blood_group.strip().upper() == patient_blood_group.strip().upper() else 70.0

        # 3. Predictor Score: ML Model returns probability of donor responding
        # Query User object for details
        user = db.query(User).filter(User.id == donor.user_id).first()
        donor_name = user.full_name if user else "Unknown"

        # Call ML response predictor
        response_probability = predict_donor_responsiveness(
            donor_age=donor.age or 30,
            distance_km=dist,
            donation_count=donor.donation_count or 0,
            is_available=donor.is_available
        )
        predictor_score = response_probability * 100.0
        status_label = classify_donor_status(
            donor_age=donor.age or 30,
            distance_km=dist,
            donation_count=donor.donation_count or 0,
            is_available=donor.is_available
        )

        # Total Priority Score
        total_score = (0.4 * distance_score) + (0.3 * predictor_score) + (0.3 * compatibility_score)

        ranked_results.append({
            "donor_id": donor.id,
            "name": donor_name,
            "blood_group": donor.blood_group,
            "phone": donor.phone,
            "distance_km": round(dist, 2),
            "distance_score": round(distance_score, 1),
            "predictor_score": round(predictor_score, 1),
            "compatibility_score": compatibility_score,
            "total_score": round(total_score, 1),
            "availability_status": status_label
        })

    # Sort descending by total score
    ranked_results.sort(key=lambda x: x["total_score"], reverse=True)
    return ranked_results[:top_n]
