import os
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
DATASET_PATH = os.path.join(BACKEND_DIR, "monitoring", "datasets", "system_metrics.csv")
MODEL_OUTPUT_PATH = os.path.join(CURRENT_DIR, "trained_model.pkl")

# Load dataset
data = pd.read_csv(DATASET_PATH)

# Encode categorical columns
data["Status"] = data["Status"].map({
    "Normal": 0,
    "Anomaly": 1
})

data["Health Check"] = data["Health Check"].map({
    "Healthy": 0,
    "Unhealthy": 1
})

data["Service Status"] = data["Service Status"].map({
    "Running": 0,
    "Degraded": 1
})

print("Dataset Loaded Successfully! - train_model.py:26")
print(data.head())


# Select input features (X)
X = data.drop(["Timestamp", "Status"], axis=1)

# Select target (y)
y = data["Status"]

print("\nInput Features (X): - train_model.py:36")
print(X.head())

print("\nTarget (y): - train_model.py:39")
print(y.head())

# Split dataset into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42
)

print("\nTraining Data Shape: - train_model.py:50")
print(X_train.shape)

print("\nTesting Data Shape: - train_model.py:53")
print(X_test.shape)

print("\nTraining Labels: - train_model.py:56")
print(y_train.shape)

print("\nTesting Labels: - train_model.py:59")
print(y_test.shape)

# Create the Random Forest model
model = RandomForestClassifier(random_state=42)

# Train the model
model.fit(X_train, y_train)

print("\nModel Trained Successfully! - train_model.py:68")

# Make predictions using the testing data
y_pred = model.predict(X_test)

# Calculate the accuracy
accuracy = accuracy_score(y_test, y_pred)

print("\nModel Accuracy: - train_model.py:76")
print(accuracy)

# Display the confusion matrix
print("\nConfusion Matrix: - train_model.py:80")
print(confusion_matrix(y_test, y_pred))

# Display the classification report
print("\nClassification Report: - train_model.py:84")
print(classification_report(y_test, y_pred))

# Save the trained model
joblib.dump(model, MODEL_OUTPUT_PATH)

print("\nModel Saved Successfully! - train_model.py:90")