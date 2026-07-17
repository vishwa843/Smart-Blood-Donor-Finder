"""ML Predictor for donor response probability."""

import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

MODEL_PATH = os.path.join(os.path.dirname(__file__), "predictor.joblib")
_model = None


def bootstrap_predictor_model():
    """
    Generate a simulated donor response history dataset and train a RandomForest model.
    Saves the model to MODEL_PATH for subsequent loads.
    """
    global _model
    print("AI Predictor: Bootstrapping simulated dataset for ML training...")

    # Generate synthetic training data
    np.random.seed(42)
    n_samples = 500

    age = np.random.randint(18, 65, size=n_samples)
    distance = np.random.uniform(0.5, 45.0, size=n_samples)
    donation_count = np.random.randint(0, 15, size=n_samples)
    is_available = np.random.choice([0, 1], p=[0.2, 0.8], size=n_samples)

    # Probability logic: high responsiveness if distance is low, is_available is true, and donation_count is stable
    base_score = 0.5 - (distance / 50.0) + (is_available * 0.4) + (donation_count * 0.02)
    # Add age effect (mild preference for 25-45 age bracket)
    base_score += np.where((age >= 25) & (age <= 45), 0.1, 0.0)

    # Convert to 0/1 target
    prob = 1.0 / (1.0 + np.exp(-base_score))  # Sigmoid conversion
    responded = np.random.binomial(1, prob)

    # Train Model
    df = pd.DataFrame({
        "age": age,
        "distance": distance,
        "donation_count": donation_count,
        "is_available": is_available
    })

    model = RandomForestClassifier(n_estimators=50, random_state=42)
    model.fit(df, responded)

    # Save Model
    try:
        joblib.dump(model, MODEL_PATH)
        print(f"AI Predictor: Successfully saved model to {MODEL_PATH}")
    except Exception as e:
        print(f"AI Predictor: Error saving model: {e}")

    _model = model


def load_model():
    """
    Load the pre-trained model. Bootstraps if missing.
    """
    global _model
    if _model is not None:
        return _model

    if os.path.exists(MODEL_PATH):
        try:
            _model = joblib.load(MODEL_PATH)
            return _model
        except Exception as e:
            print(f"AI Predictor: Failed to load model from file: {e}. Re-training...")

    bootstrap_predictor_model()
    return _model


def predict_donor_responsiveness(
    donor_age: int,
    distance_km: float,
    donation_count: int,
    is_available: bool
) -> float:
    """
    Predict probability of donor responding (0.0 to 1.0).
    """
    model = load_model()

    if model is None:
        # Fallback deterministic math
        base = 0.8
        if distance_km > 25.0:
            base -= 0.3
        elif distance_km > 10.0:
            base -= 0.15
        if not is_available:
            base -= 0.5
        base += min(0.1, donation_count * 0.01)
        return max(0.05, min(0.95, base))

    try:
        # Features: age, distance, donation_count, is_available
        input_data = pd.DataFrame([{
            "age": donor_age,
            "distance": distance_km,
            "donation_count": donation_count,
            "is_available": 1 if is_available else 0
        }])
        probabilities = model.predict_proba(input_data)
        # Class 1 (responded) probability
        return float(probabilities[0][1])
    except Exception as e:
        print(f"AI Predictor: Inference error: {e}")
        return 0.5


def classify_donor_status(
    donor_age: int,
    distance_km: float,
    donation_count: int,
    is_available: bool
) -> str:
    """
    Classify donor status: "Likely to Accept", "Likely Busy", "Likely Offline".
    """
    if not is_available:
        return "Likely Offline"

    prob = predict_donor_responsiveness(donor_age, distance_km, donation_count, is_available)
    if prob >= 0.70:
        return "Likely to Accept"
    elif prob >= 0.30:
        return "Likely Busy"
    else:
        return "Likely Offline"

