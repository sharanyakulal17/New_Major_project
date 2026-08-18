import os
import joblib
import pandas as pd

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
MODEL_PATH = os.path.join(BACKEND_DIR, "models", "trained_model.pkl")
DATASET_PATH = os.path.join(BACKEND_DIR, "monitoring", "datasets", "system_metrics.csv")

try:
    from healing.self_heal import self_heal
except ImportError:
    import sys
    sys.path.append(BACKEND_DIR)
    from healing.self_heal import self_heal

# Load trained model
model = joblib.load(MODEL_PATH) if os.path.exists(MODEL_PATH) else None


def detect_latest_anomaly():
    if not os.path.exists(DATASET_PATH):
        print(f"Dataset not found at {DATASET_PATH}")
        return "Normal"

    # Read dataset
    data = pd.read_csv(DATASET_PATH)
    if data.empty:
        print("Dataset is empty.")
        return "Normal"

    # Take the latest row
    latest = data.iloc[[-1]].copy()

    # Encode categorical columns
    latest["Health Check"] = latest["Health Check"].map({
        "Healthy": 0,
        "Unhealthy": 1
    }).fillna(0)

    latest["Service Status"] = latest["Service Status"].map({
        "Running": 0,
        "Degraded": 1
    }).fillna(0)

    # Remove columns not used during training
    for col in ["Timestamp", "Status"]:
        if col in latest.columns:
            latest = latest.drop(col, axis=1)

    if model is not None:
        prediction = model.predict(latest)
        result = "Anomaly" if prediction[0] == 1 else "Normal"
    else:
        # Heuristic fallback if model not loaded
        cpu = latest.get("CPU Usage (%)", 0).values[0]
        mem = latest.get("Memory Usage (%)", 0).values[0]
        result = "Anomaly" if cpu > 80 or mem > 80 else "Normal"

    print(f"Prediction: {result} - detect_anomaly.py")

    self_heal(result)
    return result


if __name__ == "__main__":
    detect_latest_anomaly()