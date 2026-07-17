"""Unit tests for Smart Blood Donor Finder API and modules."""

import pytest
from app.utils.geo import calculate_distance
from app.ai.matcher import is_compatible
from app.ai.predictor import predict_donor_responsiveness


def test_geo_distance():
    # Distance from Chennai (13.0827, 80.2707) to Bangalore (12.9716, 77.5946) ~ 290 km
    dist = calculate_distance(13.0827, 80.2707, 12.9716, 77.5946)
    assert dist > 250.0
    assert dist < 320.0


def test_blood_compatibility():
    # O- is universal donor
    assert is_compatible("O-", "A+") is True
    assert is_compatible("O-", "O-") is True
    assert is_compatible("O-", "AB-") is True

    # AB+ can only donate to AB+
    assert is_compatible("AB+", "A+") is False
    assert is_compatible("AB+", "AB+") is True

    # A+ compatible recipients
    assert is_compatible("A+", "AB+") is True
    assert is_compatible("A+", "O+") is False


def test_predictor_fallback():
    # If model is not loaded, it should return a fallback probability between 0.0 and 1.0
    prob = predict_donor_responsiveness(30, 5.0, 3, True)
    assert 0.0 <= prob <= 1.0

    # Closer available donors with history should have higher responsiveness
    prob_close = predict_donor_responsiveness(30, 2.0, 10, True)
    prob_far = predict_donor_responsiveness(30, 40.0, 0, False)
    assert prob_close > prob_far


def test_ai_accuracy_and_ranking_validation():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.database.base import Base
    from app.models.user import User
    from app.models.donor import Donor
    from app.models.patient import Patient
    from app.models.hospital import Hospital
    from app.models.blood_request import BloodRequest
    from app.models.donation import Donation
    from app.ai.matcher import rank_donors

    # Setup in-memory SQLite database
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    try:
        # Create test users
        u1 = User(email="donor1@test.com", hashed_password="hash", role="donor", full_name="Donor One")
        u2 = User(email="donor2@test.com", hashed_password="hash", role="donor", full_name="Donor Two")
        u3 = User(email="donor3@test.com", hashed_password="hash", role="donor", full_name="Donor Three")
        db.add_all([u1, u2, u3])
        db.commit()

        # Donor 1: Very close (0.5km), Healthy, Available -> High Priority
        d1 = Donor(
            user_id=u1.id, blood_group="O+", phone="123", age=30, gender="M",
            address="A", city="Chennai", latitude=13.0820, longitude=80.2700,
            is_available=True, health_status="Healthy"
        )
        
        # Donor 2: Further away (approx 5.0km), Healthy, Available
        d2 = Donor(
            user_id=u2.id, blood_group="O+", phone="456", age=35, gender="F",
            address="B", city="Chennai", latitude=13.1200, longitude=80.3000,
            is_available=True, health_status="Healthy"
        )

        # Donor 3: Close (0.5km), but Deferred/Sick -> Excluded!
        d3 = Donor(
            user_id=u3.id, blood_group="O+", phone="789", age=40, gender="M",
            address="C", city="Chennai", latitude=13.0820, longitude=80.2700,
            is_available=True, health_status="Deferred"
        )

        db.add_all([d1, d2, d3])
        db.commit()

        # Run AI Smart Match Recommendations
        recommendations = rank_donors(
            db=db,
            patient_blood_group="O+",
            target_lat=13.0827,
            target_lon=80.2707,
            max_radius_km=10.0,
            top_n=10
        )

        # Assertions:
        # 1. Deferred donor 3 must be excluded from recommendations list
        assert len(recommendations) == 2
        
        # 2. Recommendations should be sorted in descending order of matching score
        assert recommendations[0]["total_score"] >= recommendations[1]["total_score"]
        
        # 3. Donor 1 (closer) should be ranked first
        assert recommendations[0]["donor_id"] == d1.id

        # 4. Must populate availability classification label
        assert recommendations[0]["availability_status"] in ["Likely to Accept", "Likely Busy", "Likely Offline"]

    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

