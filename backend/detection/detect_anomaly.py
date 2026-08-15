from healing.self_heal import self_heal
import joblib
import pandas as pd

# Load trained model
model = joblib.load("models/trained_model.pkl")


def detect_latest_anomaly():

    # Read dataset
    data = pd.read_csv("monitoring/datasets/system_metrics.csv")

    # Take the latest row
    latest = data.iloc[[-1]].copy()

    # Encode categorical columns
    latest["Health Check"] = latest["Health Check"].map({
        "Healthy": 0,
        "Unhealthy": 1
    })

    latest["Service Status"] = latest["Service Status"].map({
        "Running": 0,
        "Degraded": 1
    })

    # Remove columns not used during training
    latest = latest.drop(["Timestamp", "Status"], axis=1)

    prediction = model.predict(latest)

    if prediction[0] == 1:
        result = "Anomaly"
    else:
        result = "Normal"

    print("Prediction: - detect_anomaly.py:38", result)

    self_heal(result)


if __name__ == "__main__":
    detect_latest_anomaly()