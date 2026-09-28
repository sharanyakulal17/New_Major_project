import os
import sys
import joblib
import pandas as pd

# Resolve backend base path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from healing.self_heal import self_heal
from services.gemini_service import generate_rca

MODEL_PATH = os.path.join(BACKEND_DIR, "models", "trained_model.pkl")
DATASET_PATH = os.path.join(BACKEND_DIR, "monitoring", "datasets", "system_metrics.csv")

# Load trained model
model = joblib.load(MODEL_PATH)


def detect_latest_anomaly():
    # Read dataset
    data = pd.read_csv(DATASET_PATH)

    # Take the latest row
    latest_row = data.iloc[-1]
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
    latest_features = latest.drop(["Timestamp", "Status"], axis=1, errors="ignore")

    prediction = model.predict(latest_features)

    rca_result = None
    if prediction[0] == 1:
        result = "Anomaly"
        print("Prediction: - detect_anomaly.py", result)

        # Build metrics dictionary from the actual latest telemetry row
        metrics = {
            "CPU Usage (%)": float(latest_row.get("CPU Usage (%)", 0.0)),
            "Memory Usage (%)": float(latest_row.get("Memory Usage (%)", 0.0)),
            "Disk Usage (%)": float(latest_row.get("Disk Usage (%)", 0.0)),
            "Response Time (ms)": float(latest_row.get("Response Time (ms)", 0.0)),
            "Running Processes": int(latest_row.get("Running Processes", 0)),
            "System Uptime": int(latest_row.get("System Uptime", 0)),
            "Bytes Sent": int(latest_row.get("Bytes Sent", 0)),
            "Bytes Received": int(latest_row.get("Bytes Received", 0))
        }

        # Safely invoke Gemini AI RCA
        try:
            rca_response = generate_rca(metrics, is_anomaly=True)
            if rca_response and rca_response.get("status") == "success":
                rca_result = rca_response.get("rca")
                print("\n--- [GEMINI ROOT CAUSE ANALYSIS] ---")
                print(rca_result)
                print("------------------------------------\n")
            else:
                err_msg = rca_response.get("error", "Analysis unavailable") if rca_response else "No response"
                print(f"Gemini RCA Notice: {err_msg}")
        except Exception as e:
            # Gemini failure must NEVER stop anomaly detection or self-healing
            print(f"Gemini RCA error suppressed: {e}")
            rca_result = None

        # Pass RCA to self_heal if available, otherwise call standard self_heal
        if rca_result:
            self_heal(result, rca=rca_result)
        else:
            self_heal(result)
    else:
        result = "Normal"
        print("Prediction: - detect_anomaly.py", result)
        self_heal(result)

    return result


if __name__ == "__main__":
    detect_latest_anomaly()