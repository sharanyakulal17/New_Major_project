import joblib
import pandas as pd

# Load the trained model
model = joblib.load("models/trained_model.pkl")

print("Model Loaded Successfully! - predict.py:7")

# Sample new system metrics
new_data = pd.DataFrame([{
    "CPU Usage (%)": 95.0,
    "Memory Usage (%)": 72.0,
    "Disk Usage (%)": 60.4,
    "Disk Read": 59208458752,
    "Disk Write": 49043329536,
    "Bytes Sent": 12994680,
    "Bytes Received": 10279550,
    "Packets Sent": 9441,
    "Packets Received": 15681,
    "Running Processes": 297,
    "System Uptime": 23907,
    "Service Status": 1,
    "Response Time (ms)": 0.0,
    "Health Check": 1
}])

# Predict
prediction = model.predict(new_data)

if prediction[0] == 0:
    print("\nPrediction: Normal - predict.py:31")
else:
    print("\nPrediction: Anomaly - predict.py:33")