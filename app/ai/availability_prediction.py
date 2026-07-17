"""Availability prediction helpers wrapper."""

from app.ai.predictor import predict_donor_responsiveness


def predict_availability(donor_data: dict) -> bool:
    """
    Predict if donor is likely to be available and respond based on ML model.
    """
    prob = predict_donor_responsiveness(
        donor_age=donor_data.get("age", 30),
        distance_km=donor_data.get("distance", 5.0),
        donation_count=donor_data.get("donation_count", 0),
        is_available=donor_data.get("is_available", True)
    )
    return prob >= 0.5
