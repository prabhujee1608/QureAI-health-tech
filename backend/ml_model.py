from pathlib import Path

import numpy as np
from sklearn.linear_model import LinearRegression

MODEL_PATH = Path(__file__).with_name("queue_wait_model.joblib")


def train_model() -> LinearRegression:
    # Deterministic synthetic history for the hackathon prototype.
    features = np.array([
        [0, 4.0, 1.0, 1.0], [3, 4.1, 1.0, 1.0], [7, 4.2, .95, 1.0],
        [12, 4.5, .90, 1.1], [18, 4.8, .84, 1.2], [24, 5.0, .80, 1.2],
        [5, 3.8, 1.1, .9], [10, 4.0, 1.08, .9], [15, 4.3, 1.0, 1.0],
    ])
    targets = np.array([3, 10, 23, 42, 66, 91, 8, 20, 40])
    model = LinearRegression().fit(features, targets)
    return model


MODEL = train_model()


def predict_wait(patients_ahead: int, average_consultation: float, doctor_available: bool, queue_movement: float) -> int:
    availability = 1.0 if doctor_available else 1.25
    prediction = MODEL.predict([[patients_ahead, average_consultation, queue_movement, availability]])[0]
    return max(4, round(float(prediction)))
