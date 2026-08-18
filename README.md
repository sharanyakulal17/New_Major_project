# Self-Healing Intelligent Cloud System (AURA-HEAL)

An end-to-end ML-based cloud orchestration system that monitors real-time system metrics, detects anomalies using trained Machine Learning models, and triggers automated remediation and self-healing actions.

---

## 📁 Repository Structure

```
Major_Project/
├── frontend/
│   └── index.html                # Interactive React Telemetry & Self-Healing Dashboard
├── backend/
│   ├── app.py                    # Flask Server registering dashboard blueprint
│   ├── dashboard/
│   │   ├── __init__.py
│   │   └── dashboard.py          # Flask Blueprint serving Frontend UI and REST APIs
│   ├── monitoring/
│   │   ├── collect_metrics.py    # Continuous psutil telemetry logger & live API sync
│   │   └── datasets/
│   │       └── system_metrics.csv# Telemetry dataset
│   ├── detection/
│   │   └── detect_anomaly.py     # Random Forest anomaly detection & healing trigger
│   ├── healing/
│   │   ├── self_heal.py          # Autonomous remediation engine
│   │   └── healing_log.txt       # Audit log history
│   ├── models/
│   │   ├── train_model.py        # Random Forest model training script
│   │   ├── predict.py            # Sample metric prediction test
│   │   └── trained_model.pkl     # Serialized Random Forest model
│   ├── preprocessing/
│   │   └── preprocess_data.py    # Feature engineering & encoding
│   ├── testing/
│   │   ├── cpu_stress.py         # Multi-core CPU load generator
│   │   ├── memory_stress.py      # RAM consumption generator
│   │   └── disk_stress.py        # Disk I/O stress generator
│   └── requirements.txt          # Python dependencies
└── README.md
```

---

## 🚀 Execution Guide

### 1. Run the Full Dashboard & Backend
```bash
cd Major_Project/backend
python3 app.py
```
- 🌐 **Dashboard UI**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- 📊 **Health Check**: [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)

### 2. Live Telemetry Data Collection
Collects CPU, RAM, Disk, Network, Processes, and Uptime every 5 seconds:
```bash
cd Major_Project/backend
python3 monitoring/collect_metrics.py
```

### 3. Automated Anomaly Detection & Self-Healing
Evaluates the latest recorded telemetry with the trained ML model and automatically triggers self-healing if an anomaly is detected:
```bash
cd Major_Project/backend
PYTHONPATH=. python3 detection/detect_anomaly.py
```

### 4. Retrain Machine Learning Model
```bash
cd Major_Project/backend
python3 models/train_model.py
```

### 5. Stress Testing (Trigger Simulated Faults)
- **CPU Stress**: `python3 testing/cpu_stress.py`
- **Memory Stress**: `python3 testing/memory_stress.py`
- **Disk Stress**: `python3 testing/disk_stress.py`
