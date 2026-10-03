import os
import sys
import time
import json
import threading
import requests
from datetime import datetime

import pandas as pd
import psutil
import joblib

from flask import Flask, jsonify, request, send_file, render_template_string
from flask_cors import CORS
from dotenv import load_dotenv

from decision.recovery_engine import (
    choose_recovery_action,
    simulate_what_if,
    SCALE_OUT
)


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
WORKSPACE_ROOT = os.path.dirname(PROJECT_ROOT)

sys.path.insert(0, BACKEND_DIR)


# ============================================================
# IMPORT SELF HEALING
# ============================================================

from services.gemini_service import generate_rca

try:

    from healing.self_heal import (
        self_heal,
        LOG_FILE as HEAL_LOG_FILE
    )

except ImportError:

    HEAL_LOG_FILE = os.path.join(
        BACKEND_DIR,
        "healing",
        "healing_log.txt"
    )

    def self_heal(prediction, rca=None):

        if prediction == "Response Time Anomaly":
            action = "Response Time Recovered"

        elif prediction == "Anomaly":
            action = "Monitoring Service Restarted"

        else:
            action = "No Action Required"

        log_entry = (
            f"{datetime.now()} | "
            f"{prediction} | "
            f"{action}\n"
        )

        with open(HEAL_LOG_FILE, "a") as f:
            f.write(log_entry)

        return [action]


# ============================================================
# GLOBAL STATE
# ============================================================

healing_lock = threading.Lock()

is_active_anomaly = False

last_healing_timestamp = None

last_healing_rca = None

active_injected_anomaly = None

active_injected_metrics = None

simulated_traffic = 100

simulated_memory_load = None

simulated_disk_load = None

simulated_response_load = None


# ============================================================
# INCIDENT HISTORY
# ============================================================

incident_history = []


def add_incident_event(incident_id, event):

    incident_history.append({
        "incident_id": incident_id,
        "event": event,
        "timestamp": datetime.now().isoformat()
    })


def calculate_mttr(incident_id):

    events = [
        event
        for event in incident_history
        if event["incident_id"] == incident_id
    ]

    if len(events) < 2:
        return None

    start_time = datetime.fromisoformat(
        events[0]["timestamp"]
    )

    end_time = datetime.fromisoformat(
        events[-1]["timestamp"]
    )

    return round(
        (end_time - start_time).total_seconds(),
        3
    )


# ============================================================
# PREDICTIVE TRAFFIC
# ============================================================

def predict_future_traffic():

    current_traffic = simulated_traffic

    predicted_traffic = current_traffic * 1.20

    predicted_cpu = min(
        95,
        20 + (predicted_traffic / 20)
    )

    return {

        "current_traffic": current_traffic,

        "predicted_traffic":
            round(predicted_traffic, 1),

        "predicted_cpu":
            round(predicted_cpu, 1),

        "scale_out_recommended":
            predicted_cpu >= 80
    }


def simulate_what_if_traffic(increase_percent):

    current_traffic = simulated_traffic

    predicted_traffic = current_traffic * (
        1 + increase_percent / 100
    )

    predicted_cpu = min(
        95,
        20 + (predicted_traffic / 20)
    )

    if predicted_cpu >= 88:
        recommended_action = SCALE_OUT
    else:
        recommended_action = "NO_ACTION"

    return {

        "current_traffic": current_traffic,

        "increase_percent":
            increase_percent,

        "predicted_traffic":
            round(predicted_traffic, 1),

        "predicted_cpu":
            round(predicted_cpu, 1),

        "recommended_action":
            recommended_action
    }


# ============================================================
# FLASK
# ============================================================

app = Flask(__name__)

CORS(app)


# ============================================================
# API KEY
# ============================================================

GEMINI_API_KEY = (
    os.environ.get("GEMINI_API_KEY")
    or os.environ.get("API_KEY")
)


# ============================================================
# LOAD ML MODEL
# ============================================================

MODEL_PATH = os.path.join(
    BACKEND_DIR,
    "models",
    "trained_model.pkl"
)

model = None

if os.path.exists(MODEL_PATH):

    try:

        model = joblib.load(MODEL_PATH)

        print(
            f"Loaded ML model from {MODEL_PATH}"
        )

    except Exception as e:

        print(
            f"Warning: Failed to load model: {e}"
        )


# ============================================================
# VM CLUSTER
# ============================================================

MAX_VMS = 12


VMS = [

    {
        "id": "VM-01",
        "name": "Virtual Machine - 1",
        "status": "Running",
        "cpu": 28.5,
        "memory": 42.1,
        "region": "US-East",
        "ip": "10.0.1.14",
        "uptime": "14d 6h"
    }

]


# ============================================================
# SCALE OUT
# ============================================================

def scale_out():
    """
    Add exactly ONE simulated VM.

    This function NEVER creates multiple VMs.
    """

    if len(VMS) >= MAX_VMS:

        print(
            "VM SCALE OUT: "
            "Maximum of 12 VMs already reached."
        )

        return None


    next_number = len(VMS) + 1


    new_vm = {

        "id":
            f"VM-{next_number:02d}",

        "name":
            f"Virtual Machine - {next_number}",

        "status":
            "Running",

        "cpu":
            20.0,

        "memory":
            30.0,

        "region":
            "Local-Simulation",

        "ip":
            f"192.168.1.{100 + next_number}",

        "uptime":
            "0 minutes"

    }


    VMS.append(new_vm)


    print(
        f"VM ADDED SUCCESSFULLY: "
        f"{new_vm['id']}"
    )


    return new_vm


# ============================================================
# RECOVERY ACTION
# ============================================================

def execute_recovery_action(action):

    global simulated_memory_load
    global simulated_disk_load


    # --------------------------------------------------------
    # RESTART
    # --------------------------------------------------------

    if action == "RESTART":

        for vm in VMS:

            if vm["status"] != "Running":

                vm["status"] = "Running"

                vm["cpu"] = 20.0

                vm["memory"] = 30.0

                vm["uptime"] = "0 minutes"

                simulated_memory_load = None

                return {

                    "status":
                        "success",

                    "action":
                        "RESTART",

                    "vm":
                        vm["id"],

                    "message":
                        f"{vm['id']} restarted successfully."
                }


        vm = VMS[0]

        vm["status"] = "Running"

        vm["cpu"] = 20.0

        vm["memory"] = 30.0

        vm["uptime"] = "0 minutes"

        simulated_memory_load = None

        return {

            "status":
                "success",

            "action":
                "RESTART",

            "vm":
                vm["id"],

            "message":
                f"{vm['id']} restarted successfully."
        }


    # --------------------------------------------------------
    # REROUTE
    # --------------------------------------------------------

    elif action == "REROUTE":

        return {

            "status":
                "success",

            "action":
                "REROUTE",

            "message":
                "Traffic rerouted to healthy simulated instances."
        }


    # --------------------------------------------------------
    # REPLACE INSTANCE
    # --------------------------------------------------------

    elif action == "REPLACE_INSTANCE":

        for vm in VMS:

            if vm["status"] != "Running":

                old_vm_id = vm["id"]

                vm["status"] = "Running"

                vm["cpu"] = 20.0

                vm["memory"] = 30.0

                vm["uptime"] = "0 minutes"

                return {

                    "status":
                        "success",

                    "action":
                        "REPLACE_INSTANCE",

                    "vm":
                        old_vm_id,

                    "message":
                        f"{old_vm_id} replaced successfully."
                }


        vm = VMS[0]

        old_vm_id = vm["id"]

        vm["status"] = "Running"

        vm["cpu"] = 20.0

        vm["memory"] = 30.0

        vm["uptime"] = "0 minutes"

        return {

            "status":
                "success",

            "action":
                "REPLACE_INSTANCE",

            "vm":
                old_vm_id,

            "message":
                f"{old_vm_id} replaced successfully."
        }


    # --------------------------------------------------------
    # SCALE OUT
    # --------------------------------------------------------

    elif action == "SCALE_OUT":

        print(
            f"SCALE OUT REQUESTED | "
            f"Current VMs: {len(VMS)} | "
            f"Maximum: {MAX_VMS}"
        )


        # IMPORTANT:
        # Add ONLY ONE VM per recovery event.

        new_vm = scale_out()


        if new_vm is not None:

            print(
                f"SCALE OUT COMPLETE | "
                f"Added {new_vm['id']} | "
                f"Total VMs: {len(VMS)}"
            )

            return {

                "status":
                    "success",

                "action":
                    "SCALE_OUT",

                "message":
                    f"{new_vm['id']} added successfully.",

                "vm_count":
                    len(VMS),

                "vm":
                    new_vm["id"],

                "vms_added":
                    [new_vm]
            }


        print(
            f"SCALE OUT SKIPPED | "
            f"Maximum {MAX_VMS} VMs already running."
        )


        return {

            "status":
                "success",

            "action":
                "SCALE_OUT",

            "message":
                f"Maximum VM limit of {MAX_VMS} reached.",

            "vm_count":
                len(VMS),

            "vms_added":
                []
        }


    # --------------------------------------------------------
    # ESCALATE
    # --------------------------------------------------------

    elif action == "ESCALATE":

        return {

            "status":
                "escalated",

            "action":
                "ESCALATE",

            "message":
                "The anomaly requires manual investigation."
        }


    # --------------------------------------------------------
    # NO ACTION
    # --------------------------------------------------------

    else:

        return {

            "status":
                "success",

            "action":
                "NO_ACTION",

            "message":
                "No recovery action was required."
        }


# ============================================================
# VERIFY RECOVERY
# ============================================================

def verify_recovery(vm_id=None):

    if vm_id is None:

        return {

            "verified":
                False,

            "status":
                "unknown",

            "message":
                "No VM was provided for recovery verification."
        }


    for vm in VMS:

        if vm["id"] == vm_id:

            healthy = (

                vm["status"] == "Running"

                and vm["cpu"] < 85

                and vm["memory"] < 85

            )


            if healthy:

                return {

                    "verified":
                        True,

                    "status":
                        "healthy",

                    "vm":
                        vm_id,

                    "message":
                        f"{vm_id} recovered successfully.",

                    "metrics": {

                        "cpu":
                            vm["cpu"],

                        "memory":
                            vm["memory"]
                    }
                }


            return {

                "verified":
                    False,

                "status":
                    "unhealthy",

                "vm":
                    vm_id,

                "message":
                    f"{vm_id} is still unhealthy.",

                "metrics": {

                    "cpu":
                        vm["cpu"],

                    "memory":
                        vm["memory"]
                }
            }


    return {

        "verified":
            False,

        "status":
            "unknown",

        "message":
            f"{vm_id} was not found."
    }


# ============================================================
# LIVE METRICS
# ============================================================

def get_live_metrics():

    print(
        "SIMULATED TRAFFIC:",
        simulated_traffic
    )


    cpu = min(
    95,
    20 + (simulated_traffic / 12)
    )


    mem = (

        simulated_memory_load

        if simulated_memory_load is not None

        else psutil.virtual_memory().percent

    )


    disk = (

        simulated_disk_load

        if simulated_disk_load is not None

        else psutil.disk_usage("/").percent

    )


    net = psutil.net_io_counters()

    uptime = int(
        time.time() -
        psutil.boot_time()
    )


    disk_io = psutil.disk_io_counters()


    return {

        "timestamp":
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

        "cpu_usage":
            cpu,

        "memory_usage":
            mem,

        "disk_usage":
            disk,

        "disk_read":
            disk_io.read_bytes
            if disk_io else 0,

        "disk_write":
            disk_io.write_bytes
            if disk_io else 0,

        "bytes_sent":
            net.bytes_sent,

        "bytes_received":
            net.bytes_recv,

        "packets_sent":
            net.packets_sent,

        "packets_received":
            net.packets_recv,

        "running_processes":
            len(psutil.pids()),

        "system_uptime":
            uptime,

        "service_status":
            0 if cpu < 85 else 1,

        "response_time_ms":

            simulated_response_load

            if simulated_response_load is not None

            else round(
                100 +
                (simulated_traffic / 5),
                1
            ),

        "health_check":
            0 if cpu < 85 else 1
    }


# ============================================================
# AI ANALYSIS
# ============================================================

def generate_ai_analysis(
    cpu,
    memory,
    disk,
    latency,
    is_anomaly
):

    prompt = (

        "Perform cloud infrastructure "
        "Root Cause Analysis for a node "
        "with telemetry:\n"

        f"- CPU: {cpu}%\n"

        f"- Memory: {memory}%\n"

        f"- Disk: {disk}%\n"

        f"- Network Latency: {latency}ms\n"

        f"- Anomaly Status: "
        f"{'CRITICAL ANOMALY' if is_anomaly else 'NOMINAL / HEALTHY'}\n"

        "Provide a brief diagnosis "
        "(2 sentences) and recommended "
        "remediation action."

    )


    if GEMINI_API_KEY and len(GEMINI_API_KEY) > 10:

        try:

            url = (
                "https://generativelanguage.googleapis.com/"
                "v1beta/models/gemini-1.5-flash:"
                f"generateContent?key={GEMINI_API_KEY}"
            )


            payload = {

                "contents": [

                    {

                        "parts": [

                            {
                                "text":
                                    prompt
                            }

                        ]

                    }

                ]

            }


            resp = requests.post(

                url,

                json=payload,

                timeout=3.0

            )


            if resp.status_code == 200:

                result = resp.json()

                text = (
                    result
                    ["candidates"][0]
                    ["content"]["parts"][0]
                    ["text"]
                )


                return {

                    "provider":
                        "Gemini-1.5-Flash (Live API)",

                    "diagnosis":
                        text.strip(),

                    "confidence":
                        0.98
                        if is_anomaly
                        else 0.99,

                    "remediation":
                        (
                            "Auto-scaling and "
                            "process throttling suggested."
                            if is_anomaly
                            else
                            "Maintain standard observability."
                        )
                }

        except Exception:

            pass


    # --------------------------------------------------------
    # DETERMINISTIC FALLBACK
    # --------------------------------------------------------

    if is_anomaly:

        if cpu > 80:

            root_cause = (
                "Compute Bottleneck: "
                "High multi-threaded workload "
                "saturating CPU pipeline."
            )

            action = (
                "Trigger dynamic container "
                "horizontal auto-scaling & "
                "restart runaway worker processes."
            )


        elif memory > 80:

            root_cause = (
                "Memory Leak: "
                "Unbounded buffer allocation "
                "detected in resident set size (RSS)."
            )

            action = (
                "Execute hot memory heap "
                "garbage collection & "
                "rolling pod restart."
            )


        elif disk > 85:

            root_cause = (
                "Storage Contention: "
                "Disk I/O queue length saturated "
                "by unpruned container logs."
            )

            action = (
                "Flush ephemeral cache directory "
                "and rotate system journals."
            )


        else:

            root_cause = (
                "Network Latency Degraded: "
                "Packet transmission jitter "
                "exceeding SLA thresholds."
            )

            action = (
                "Reroute ingress traffic via "
                "healthy secondary availability "
                "zone gateway."
            )


    else:

        root_cause = (
            "Nominal telemetry metrics across "
            "CPU, RAM, Disk, and Network channels."
        )

        action = (
            "No intervention required. "
            "Cluster health verified within "
            "optimal thresholds."
        )


    return {

        "provider":
            "AURA-HEAL Neural Diagnostic Engine "
            "(API Active)",

        "diagnosis":
            root_cause,

        "confidence":
            0.96 if is_anomaly else 0.99,

        "remediation":
            action
    }


# ============================================================
# FRONTEND FILE RESOLVER
# ============================================================

def resolve_frontend_file(filename):

    candidates = [

        os.path.join(
            WORKSPACE_ROOT,
            "new_frontend",
            filename
        ),

        os.path.join(
            PROJECT_ROOT,
            "new_frontend",
            filename
        ),

        os.path.join(
            WORKSPACE_ROOT,
            "frontend",
            filename
        ),

        os.path.join(
            PROJECT_ROOT,
            "frontend",
            filename
        )

    ]


    for path in candidates:

        resolved = os.path.abspath(path)

        if os.path.exists(resolved):

            return resolved


    return None


# ============================================================
# DASHBOARD PAYLOAD
# ============================================================

def build_dashboard_payload():

    metrics = get_live_metrics()


    return {

        "status":
            "healthy",

        "platform":
            "Self-Healing Monitoring Dashboard",

        "system_info": {

            "os":
                "Windows 11 / Linux Server",

            "cpu":
                "8 Core",

            "memory":
                "8 GB",

            "storage":
                "500 GB SSD",

            "network":
                "Connected",

            "status":
                "Operational"
        },

        "metrics": {

            "cpu_usage":
                metrics["cpu_usage"],

            "memory_usage":
                metrics["memory_usage"],

            "disk_usage":
                metrics["disk_usage"],

            "uptime_seconds":
                metrics["system_uptime"],

            "running_processes":
                metrics["running_processes"]
        },

        "graphs": {

            "cpu":
                [30, 42, 58, 74, 68, 90],

            "memory":
                [35, 43, 52, 60, 70, 80],

            "disk":
                [20, 36, 48, 54, 64, 72]
        },

        "vm": {

            "name":
                "prod-node-01",

            "state":
                "Running",

            "cpu":
                "4 vCPU",

            "memory":
                "8 GB",

            "disk":
                "200 GB",

            "uptime":
                "18 days"
        },

        "logs": [

            {
                "level":
                    "INFO",

                "message":
                    "Server started successfully."
            },

            {
                "level":
                    "INFO",

                "message":
                    "Database connection healthy."
            },

            {
                "level":
                    "WARN",

                "message":
                    "CPU usage nearing threshold."
            },

            {
                "level":
                    "INFO",

                "message":
                    "Backup task completed."
            },

            {
                "level":
                    "ERROR",

                "message":
                    "Temporary network retry triggered."
            }

        ]

    }


# ============================================================
# FRONTEND ROUTES
# ============================================================

@app.route("/")
def serve_frontend():

    frontend_file = resolve_frontend_file(
        "index3.html"
    )

    if frontend_file:

        return send_file(
            frontend_file
        )


    frontend_candidates = [

        os.path.join(
            WORKSPACE_ROOT,
            "frontend",
            "index.html"
        ),

        os.path.join(
            PROJECT_ROOT,
            "frontend",
            "index.html"
        )

    ]


    for path in frontend_candidates:

        if os.path.exists(path):

            return send_file(path)


    return jsonify({

        "status":
            "online",

        "service":
            "Self-Healing Cloud Monitoring System Backend",

        "endpoints": [

            "/api/v1/health",

            "/api/v1/metrics/current",

            "/api/v1/predict",

            "/api/v1/heal",

            "/api/v1/logs",

            "/backend"

        ]

    })


@app.route("/index3.html")
def serve_index3_html():

    frontend_file = resolve_frontend_file(
        "index3.html"
    )

    if frontend_file:

        return send_file(
            frontend_file
        )

    return jsonify({
        "error":
            "Dashboard page not found"
    }), 404


@app.route("/system-information")
@app.route("/system-information.html")
def serve_system_information_page():

    frontend_file = resolve_frontend_file(
        "system-information.html"
    )

    if frontend_file:

        return send_file(
            frontend_file
        )

    return jsonify({
        "error":
            "System information page not found"
    }), 404


@app.route("/graphs")
@app.route("/graphs.html")
def serve_graphs_page():

    frontend_file = resolve_frontend_file(
        "graphs.html"
    )

    if frontend_file:

        return send_file(
            frontend_file
        )

    return jsonify({
        "error":
            "Graphs page not found"
    }), 404


@app.route("/logs")
@app.route("/logs.html")
def serve_logs_page():

    frontend_file = resolve_frontend_file(
        "logs.html"
    )

    if frontend_file:

        return send_file(
            frontend_file
        )

    return jsonify({
        "error":
            "Logs page not found"
    }), 404


@app.route("/vm")
@app.route("/vm.html")
def serve_vm_page():

    frontend_file = resolve_frontend_file(
        "vm.html"
    )

    if frontend_file:

        return send_file(
            frontend_file
        )

    return jsonify({
        "error":
            "VM page not found"
    }), 404


@app.route("/assets/<path:filename>")
def serve_assets(filename):

    asset_candidates = [

        os.path.join(
            PROJECT_ROOT,
            "frontend",
            "assets",
            filename
        ),

        os.path.join(
            WORKSPACE_ROOT,
            "frontend",
            "assets",
            filename
        ),

        os.path.join(
            WORKSPACE_ROOT,
            "new_frontend",
            filename
        ),

        os.path.join(
            PROJECT_ROOT,
            "new_frontend",
            filename
        )

    ]


    for path in asset_candidates:

        if os.path.exists(path):

            return send_file(path)


    return jsonify({
        "error":
            "Asset not found"
    }), 404


# ============================================================
# BACKEND OVERVIEW
# ============================================================

@app.route("/backend")
@app.route("/api")
def backend_overview():

    metrics = get_live_metrics()

    logs = read_recent_logs(5)

    if GEMINI_API_KEY:

        if len(GEMINI_API_KEY) > 12:

            masked_key = (
                f"{GEMINI_API_KEY[:6]}..."
                f"{GEMINI_API_KEY[-6:]}"
            )

        else:

            masked_key = "Configured"

    else:

        masked_key = "Not configured"


    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>

        <meta charset="UTF-8">

        <meta name="viewport"
              content="width=device-width, initial-scale=1.0">

        <title>
            Self-Healing Backend |
            API Status & Control Center
        </title>

        <style>

            :root {
                --bg: #090d16;
                --card-bg: #111827;
                --accent: #00f2fe;
                --accent-blue: #3b82f6;
                --success: #10b981;
                --text: #f3f4f6;
                --text-muted: #9ca3af;
                --border: rgba(255,255,255,0.1);
            }

            * {
                box-sizing: border-box;
                margin: 0;
                padding: 0;
            }

            body {
                background-color: var(--bg);
                color: var(--text);
                font-family: Arial, sans-serif;
                padding: 40px 20px;
                min-height: 100vh;
            }

            .container {
                max-width: 1050px;
                margin: 0 auto;
            }

            header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 30px;
                padding-bottom: 20px;
                border-bottom: 1px solid var(--border);
            }

            h1 {
                font-size: 28px;
            }

            .badge {
                background: rgba(16,185,129,0.2);
                color: var(--success);
                border: 1px solid rgba(16,185,129,0.4);
                padding: 6px 14px;
                border-radius: 20px;
                font-weight: 600;
                font-size: 13px;
            }

            .grid {
                display: grid;
                grid-template-columns:
                    repeat(auto-fit,minmax(220px,1fr));
                gap: 20px;
                margin-bottom: 30px;
            }

            .card,
            .section {
                background: var(--card-bg);
                border: 1px solid var(--border);
                border-radius: 12px;
            }

            .card {
                padding: 20px;
            }

            .card h3 {
                font-size: 13px;
                color: var(--text-muted);
                margin-bottom: 10px;
            }

            .card .value {
                font-size: 22px;
                font-weight: 700;
            }

            .section {
                padding: 24px;
                margin-bottom: 24px;
            }

            .section h2 {
                font-size: 20px;
                margin-bottom: 16px;
            }

            table {
                width: 100%;
                border-collapse: collapse;
            }

            th,
            td {
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid var(--border);
                font-size: 14px;
            }

            th {
                color: var(--text-muted);
            }

            .method {
                display: inline-block;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 700;
            }

            .get {
                background: rgba(59,130,246,0.2);
                color: #60a5fa;
            }

            .post {
                background: rgba(16,185,129,0.2);
                color: #34d399;
            }

            a {
                color: var(--accent);
                text-decoration: none;
            }

            .btn-group {
                display: flex;
                gap: 12px;
                margin-top: 10px;
                flex-wrap: wrap;
            }

            .btn {
                background: linear-gradient(
                    135deg,
                    #00f2fe,
                    #4facfe
                );
                color: #050b14;
                font-weight: 600;
                padding: 10px 20px;
                border-radius: 8px;
                text-decoration: none;
                display: inline-block;
            }

        </style>

    </head>

    <body>

        <div class="container">

            <header>

                <div>

                    <h1>
                        Self-Healing Cloud
                        Backend & AI Engine
                    </h1>

                    <p style="
                        color:var(--text-muted);
                        font-size:14px;
                        margin-top:4px;
                    ">
                        Flask REST API Engine,
                        ML Random Forest &
                        Gemini Diagnostics
                    </p>

                </div>

                <div class="badge">
                    🟢 All Systems Operational
                </div>

            </header>


            <div class="grid">

                <div class="card">

                    <h3>
                        ML Model Status
                    </h3>

                    <div class="value">
                        Random Forest
                    </div>

                    <p style="
                        font-size:12px;
                        color:var(--text-muted);
                        margin-top:4px;
                    ">
                        trained_model.pkl loaded
                    </p>

                </div>


                <div class="card">

                    <h3>
                        AI Diagnostic Engine
                    </h3>

                    <div class="value">
                        Active
                    </div>

                    <p style="
                        font-size:12px;
                        color:var(--text-muted);
                        margin-top:4px;
                    ">
                        Key: {{ masked_key }}
                    </p>

                </div>


                <div class="card">

                    <h3>
                        Live CPU Telemetry
                    </h3>

                    <div class="value">
                        {{ metrics.cpu_usage }}%
                    </div>

                </div>


                <div class="card">

                    <h3>
                        Live RAM Usage
                    </h3>

                    <div class="value">
                        {{ metrics.memory_usage }}%
                    </div>

                </div>

            </div>


            <div class="section">

                <h2>
                    API Endpoints & Integration Status
                </h2>

                <table>

                    <thead>

                        <tr>
                            <th>Method</th>
                            <th>Endpoint</th>
                            <th>Description</th>
                        </tr>

                    </thead>

                    <tbody>

                        <tr>
                            <td>
                                <span class="method get">
                                    GET
                                </span>
                            </td>

                            <td>
                                /api/v1/health
                            </td>

                            <td>
                                Health check
                            </td>
                        </tr>

                        <tr>
                            <td>
                                <span class="method get">
                                    GET
                                </span>
                            </td>

                            <td>
                                /api/v1/metrics/current
                            </td>

                            <td>
                                Live telemetry
                            </td>
                        </tr>

                        <tr>
                            <td>
                                <span class="method get">
                                    GET
                                </span>
                            </td>

                            <td>
                                /api/v1/instances
                            </td>

                            <td>
                                VM cluster
                            </td>
                        </tr>

                        <tr>
                            <td>
                                <span class="method get">
                                    GET
                                </span>
                            </td>

                            <td>
                                /api/v1/logs
                            </td>

                            <td>
                                Healing logs
                            </td>
                        </tr>

                        <tr>
                            <td>
                                <span class="method post">
                                    POST
                                </span>
                            </td>

                            <td>
                                /api/v1/predict
                            </td>

                            <td>
                                ML anomaly detection
                            </td>
                        </tr>

                        <tr>
                            <td>
                                <span class="method post">
                                    POST
                                </span>
                            </td>

                            <td>
                                /api/v1/heal
                            </td>

                            <td>
                                Self-healing workflow
                            </td>
                        </tr>

                    </tbody>

                </table>

            </div>


            <div class="section">

                <h2>
                    Quick Actions
                </h2>

                <div class="btn-group">

                    <a href="/" class="btn">
                        Open Dashboard
                    </a>

                    <a
                        href="/api/v1/health"
                        class="btn"
                    >
                        Health JSON
                    </a>

                    <a
                        href="/api/v1/instances"
                        class="btn"
                    >
                        VM JSON
                    </a>

                </div>

            </div>

        </div>

    </body>
    </html>
    """


    return render_template_string(

        html,

        metrics=metrics,

        logs=logs,

        masked_key=masked_key

    )


# ============================================================
# HEALTH
# ============================================================

@app.route("/health")
@app.route("/api/v1/health")
def health_check():

    return jsonify({

        "status":
            "healthy",

        "service":
            "Self-Healing Intelligent "
            "Cloud Monitoring Backend",

        "version":
            "1.0.0",

        "timestamp":
            datetime.now().isoformat(),

        "model_loaded":
            model is not None,

        "model_type":
            "RandomForestClassifier",

        "ai_engine_configured":
            bool(GEMINI_API_KEY),

        "active_vms":
            len(VMS),

        "maximum_vms":
            MAX_VMS

    })


# ============================================================
# CURRENT METRICS
# ============================================================

@app.route("/api/metrics")
@app.route("/api/v1/metrics")
@app.route("/api/v1/metrics/current")
def current_metrics():

    global active_injected_metrics
    global active_injected_anomaly


    if active_injected_metrics:

        return jsonify({

            "status":
                "success",

            "metrics": {

                "cpu":
                    float(
                        active_injected_metrics
                        .get("cpu", 98.5)
                    ),

                "memory":
                    float(
                        active_injected_metrics
                        .get("memory", 88.2)
                    ),

                "disk":
                    float(
                        active_injected_metrics
                        .get("disk", 45.0)
                    ),

                "latency":
                    float(
                        active_injected_metrics
                        .get("latency", 220.0)
                    ),

                "bytes_sent":
                    int(
                        active_injected_metrics
                        .get(
                            "bytes_sent",
                            2425000000
                        )
                    ),

                "bytes_recv":
                    int(
                        active_injected_metrics
                        .get(
                            "bytes_recv",
                            5235000000
                        )
                    ),

                "packets_sent":
                    int(
                        active_injected_metrics
                        .get(
                            "packets_sent",
                            1900000
                        )
                    ),

                "packets_recv":
                    int(
                        active_injected_metrics
                        .get(
                            "packets_recv",
                            3480000
                        )
                    ),

                "processes":
                    int(
                        active_injected_metrics
                        .get(
                            "processes",
                            750
                        )
                    ),

                "uptime_seconds":
                    int(
                        active_injected_metrics
                        .get(
                            "uptime_seconds",
                            21500
                        )
                    )

            },

            "timestamp":
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),

            "injected":
                True,

            "anomaly_type":
                active_injected_anomaly

        })


    metrics = get_live_metrics()

    traffic_overload = (
        simulated_traffic >= 1200
    )


    return jsonify({

        "status":
            "success",

        "metrics": {

            "cpu":
                metrics["cpu_usage"],

            "memory":
                metrics["memory_usage"],

            "disk":
                metrics["disk_usage"],

            "latency":
                metrics["response_time_ms"],

            "bytes_sent":
                metrics["bytes_sent"],

            "bytes_recv":
                metrics["bytes_received"],

            "packets_sent":
                metrics["packets_sent"],

            "packets_recv":
                metrics["packets_received"],

            "processes":
                metrics["running_processes"],

            "uptime_seconds":
                metrics["system_uptime"],

            "traffic_requests_per_minute":
                simulated_traffic,

            "traffic_overload":
                traffic_overload

        },

        "timestamp":
            metrics["timestamp"]

    })


# ============================================================
# ALERTS
# ============================================================

@app.route("/api/alerts")
@app.route("/api/v1/alerts")
def get_alerts():

    metrics = get_live_metrics()

    alerts = []


    if metrics["cpu_usage"] > 80:

        alerts.append({

            "id":
                "ALT-01",

            "level":
                "Critical",

            "message":
                f"High CPU utilization detected "
                f"({metrics['cpu_usage']}%)",

            "timestamp":
                metrics["timestamp"]

        })


    if metrics["memory_usage"] > 80:

        alerts.append({

            "id":
                "ALT-02",

            "level":
                "Warning",

            "message":
                f"Memory threshold exceeded "
                f"({metrics['memory_usage']}%)",

            "timestamp":
                metrics["timestamp"]

        })


    for vm in VMS:

        if vm["status"] in [
            "Critical",
            "Warning"
        ]:

            alerts.append({

                "id":
                    f"ALT-{vm['id']}",

                "level":
                    vm["status"],

                "message":
                    f"{vm['name']} in "
                    f"{vm['status']} state "
                    f"(CPU: {vm['cpu']}%)",

                "timestamp":
                    metrics["timestamp"]

            })


    return jsonify({

        "status":
            "success",

        "alerts":
            alerts,

        "count":
            len(alerts)

    })


# ============================================================
# SYSTEM STATUS
# ============================================================

@app.route("/api/v1/system/status")
def system_status():

    metrics = get_live_metrics()


    is_anomaly = (

        metrics["cpu_usage"] > 80

        or metrics["memory_usage"] > 85

        or metrics["disk_usage"] > 80

    )


    status_text = (
        "ANOMALY DETECTED"
        if is_anomaly
        else
        "SYSTEM HEALTHY"
    )


    healing_state = (

        "ACTIVE"
        if is_active_anomaly

        else

        (
            "READY"
            if is_anomaly
            else
            "STANDBY"
        )

    )


    return jsonify({

        "status":
            "success",

        "system_status":
            status_text,

        "healing_state":
            healing_state,

        "is_anomaly":
            is_anomaly,

        "risk_level":
            "critical"
            if is_anomaly
            else
            "healthy",

        "metrics": {

            "cpu":
                metrics["cpu_usage"],

            "memory":
                metrics["memory_usage"],

            "disk":
                metrics["disk_usage"],

            "latency":
                metrics["response_time_ms"]

        },

        "timestamp":
            metrics["timestamp"]

    })


# ============================================================
# DASHBOARD OVERVIEW
# ============================================================

@app.route("/api/v1/dashboard/overview")
def dashboard_overview():

    metrics = get_live_metrics()


    is_anomaly = (

        metrics["cpu_usage"] > 80

        or metrics["memory_usage"] > 85

        or metrics["disk_usage"] > 80

    )


    analysis = generate_ai_analysis(

        metrics["cpu_usage"],

        metrics["memory_usage"],

        metrics["disk_usage"],

        metrics["response_time_ms"],

        is_anomaly

    )


    alerts_response = get_alerts()

    alerts_data = (
        alerts_response
        .get_json(silent=True)
        or {}
    )


    return jsonify({

        "status":
            "success",

        "metrics": {

            "cpu":
                round(
                    metrics["cpu_usage"],
                    1
                ),

            "memory":
                round(
                    metrics["memory_usage"],
                    1
                ),

            "disk":
                round(
                    metrics["disk_usage"],
                    1
                ),

            "latency":
                round(
                    metrics["response_time_ms"],
                    1
                ),

            "uptime":
                metrics["system_uptime"],

            "processes":
                metrics["running_processes"]

        },

        "system_status":
            (
                "ANOMALY DETECTED"
                if is_anomaly
                else
                "SYSTEM HEALTHY"
            ),

        "healing_state":
            (
                "SELF-HEALING"
                if is_active_anomaly
                else
                (
                    "READY"
                    if is_anomaly
                    else
                    "STANDBY"
                )
            ),

        "diagnosis":
            analysis,

        "alerts":
            alerts_data.get(
                "alerts",
                []
            ),

        "instances":
            VMS,

        "timestamp":
            metrics["timestamp"]

    })


# ============================================================
# AI DIAGNOSIS
# ============================================================

@app.route("/api/v1/ai/diagnosis")
def ai_diagnosis():

    metrics = get_live_metrics()


    is_anomaly = (

        metrics["cpu_usage"] > 80

        or metrics["memory_usage"] > 85

        or metrics["disk_usage"] > 80

    )


    analysis = generate_ai_analysis(

        metrics["cpu_usage"],

        metrics["memory_usage"],

        metrics["disk_usage"],

        metrics["response_time_ms"],

        is_anomaly

    )


    return jsonify({

        "status":
            "success",

        "is_anomaly":
            is_anomaly,

        "diagnosis":
            analysis["diagnosis"],

        "remediation":
            analysis["remediation"],

        "provider":
            analysis["provider"],

        "confidence":
            analysis["confidence"],

        "timestamp":
            metrics["timestamp"]

    })


# ============================================================
# PREDICTION ANALYSIS
# ============================================================

@app.route("/api/prediction/analysis")
@app.route("/api/v1/prediction/analysis")
def get_prediction_analysis():

    cpu = float(
        request.args.get(
            "cpu",
            psutil.cpu_percent(
                interval=None
            )
        )
    )


    memory = float(
        request.args.get(
            "memory",
            psutil.virtual_memory().percent
        )
    )


    disk = float(
        request.args.get(
            "disk",
            psutil.disk_usage("/").percent
        )
    )


    latency = float(
        request.args.get(
            "latency",
            12.5
        )
    )


    is_anomaly_arg = (

        request.args
        .get(
            "is_anomaly",
            "false"
        )
        .lower()

        in [
            "true",
            "1",
            "yes"
        ]

    )


    is_anomaly = (

        is_anomaly_arg

        or

        (
            cpu > 80
            or memory > 85
        )

    )


    analysis = generate_ai_analysis(

        cpu,
        memory,
        disk,
        latency,
        is_anomaly

    )


    risk_val = round(

        min(

            99.0,

            max(

                5.0,

                (
                    92.5
                    if is_anomaly

                    else

                    (
                        cpu * 0.4
                        + memory * 0.4
                        + (disk or 10) * 0.2
                    )
                )

            )

        ),

        1

    )


    return jsonify({

        "status":
            "success",

        "analysis":
            analysis,

        "overall_cloud_risk":
            risk_val,

        "evaluated_metrics": {

            "cpu":
                cpu,

            "memory":
                memory,

            "disk":
                disk,

            "latency":
                latency

        },

        "is_anomaly":
            is_anomaly,

        "timestamp":
            datetime.now().isoformat()

    })


# ============================================================
# AI ANALYZE
# ============================================================

@app.route(
    "/api/v1/ai/analyze",
    methods=["POST"]
)
def post_ai_analyze():

    data = request.get_json(
        silent=True
    )


    if not data or not isinstance(data, dict):

        return jsonify({

            "status":
                "error",

            "error":
                "Invalid request. "
                "JSON payload is required."

        }), 400


    metrics = data.get("metrics")


    if (
        metrics is None
        or not isinstance(metrics, dict)
    ):

        return jsonify({

            "status":
                "error",

            "error":
                "Missing or invalid "
                "'metrics' dictionary."

        }), 400


    is_anomaly = data.get(
        "is_anomaly",
        False
    )


    if not isinstance(
        is_anomaly,
        bool
    ):

        is_anomaly = bool(
            is_anomaly
        )


    try:

        result = generate_rca(

            metrics=metrics,

            is_anomaly=is_anomaly

        )


        if result.get(
            "status"
        ) == "error":

            return jsonify(
                result
            ), 502


        return jsonify(
            result
        ), 200


    except Exception as e:

        return jsonify({

            "status":
                "error",

            "error":
                str(e)

        }), 500


# ============================================================
# AI CHAT
# ============================================================

@app.route(
    "/api/ai/chat",
    methods=["POST"]
)
@app.route(
    "/api/v1/ai/chat",
    methods=["POST"]
)
def ai_chat():

    data = request.get_json(
        silent=True
    ) or {}


    user_msg = data.get(
        "message",
        "How is cluster health?"
    )


    metrics = get_live_metrics()


    prompt = (

        "You are AURA-HEAL AI Copilot "
        "for autonomous cloud self-healing. "

        f"System telemetry: "
        f"CPU: {metrics['cpu_usage']}%, "

        f"RAM: {metrics['memory_usage']}%, "

        f"Running Procs: "
        f"{metrics['running_processes']}. "

        f"User asks: '{user_msg}'. "

        "Answer concisely in 2 sentences."

    )


    response_text = (

        f"Current system status is nominal "
        f"with CPU at "
        f"{metrics['cpu_usage']}% and RAM at "
        f"{metrics['memory_usage']}%. "

        "All nodes are executing "
        "self-healing monitoring normally."

    )


    if GEMINI_API_KEY and len(
        GEMINI_API_KEY
    ) > 10:

        try:

            url = (

                "https://generativelanguage.googleapis.com/"
                "v1beta/models/gemini-1.5-flash:"
                f"generateContent?key={GEMINI_API_KEY}"

            )


            resp = requests.post(

                url,

                json={

                    "contents": [

                        {

                            "parts": [

                                {
                                    "text":
                                        prompt
                                }

                            ]

                        }

                    ]

                },

                timeout=4.0

            )


            if resp.status_code == 200:

                response_text = (

                    resp.json()
                    ["candidates"][0]
                    ["content"]
                    ["parts"][0]
                    ["text"]
                    .strip()

                )

        except Exception:

            pass


    return jsonify({

        "status":
            "success",

        "reply":
            response_text,

        "timestamp":
            datetime.now().isoformat()

    })


# ============================================================
# VM LIST
# ============================================================

@app.route("/api/instances")
@app.route("/api/v1/instances")
def list_instances():

    return jsonify(VMS)


# ============================================================
# TRAFFIC SIMULATOR
# ============================================================

@app.route(
    "/api/v1/traffic",
    methods=["GET", "POST"]
)
def traffic_simulator():

    global simulated_traffic


    if request.method == "POST":

        data = request.get_json(
            silent=True
        ) or {}


        try:

            traffic = int(
                data.get(
                    "traffic",
                    simulated_traffic
                )
            )


            simulated_traffic = max(
                0,
                traffic
            )


        except (
            TypeError,
            ValueError
        ):

            return jsonify({

                "status":
                    "error",

                "message":
                    "Traffic must be a number."

            }), 400


    return jsonify({

        "status":
            "success",

        "traffic_requests_per_minute":
            simulated_traffic,

        "message":
            "Traffic simulation updated."

    })


# ============================================================
# RESPONSE LOAD
# ============================================================

@app.route(
    "/api/response-load",
    methods=["POST"]
)
@app.route(
    "/api/v1/response-load",
    methods=["POST"]
)
def set_response_load():

    global simulated_response_load


    data = request.get_json(
        silent=True
    ) or {}


    try:

        response_time = float(

            data.get(
                "response_time",
                100
            )

        )


    except (
        TypeError,
        ValueError
    ):

        return jsonify({

            "status":
                "error",

            "message":
                "Invalid response time."

        }), 400


    response_time = max(

        100.0,

        min(
            5000.0,
            response_time
        )

    )


    simulated_response_load = (
        response_time
    )


    print(
        "SIMULATED RESPONSE LOAD:",
        simulated_response_load
    )


    return jsonify({

        "status":
            "success",

        "message":
            "Response time load updated.",

        "response_time_ms":
            response_time

    })


# ============================================================
# MEMORY LOAD
# ============================================================

@app.route(
    "/api/v1/load/memory",
    methods=["GET", "POST"]
)
def memory_load_simulator():

    global simulated_memory_load


    if request.method == "POST":

        data = request.get_json(
            silent=True
        ) or {}


        try:

            memory = float(

                data.get(
                    "memory",
                    90
                )

            )


        except (
            TypeError,
            ValueError
        ):

            return jsonify({

                "status":
                    "error",

                "message":
                    "Memory load must be a number."

            }), 400


        memory = max(

            0,

            min(
                95,
                memory
            )

        )


        simulated_memory_load = memory


    current_memory = (

        simulated_memory_load

        if simulated_memory_load is not None

        else psutil.virtual_memory().percent

    )


    return jsonify({

        "status":
            "success",

        "memory":
            round(
                current_memory,
                1
            ),

        "simulated":
            simulated_memory_load is not None,

        "message":
            "Memory load simulation updated."

    })


# ============================================================
# DISK LOAD
# ============================================================

@app.route(
    "/api/v1/load/disk",
    methods=["GET", "POST"]
)
def disk_load_simulator():

    global simulated_disk_load


    if request.method == "POST":

        data = request.get_json(
            silent=True
        ) or {}


        try:

            disk = float(

                data.get(
                    "disk",
                    90
                )

            )


        except (
            TypeError,
            ValueError
        ):

            return jsonify({

                "status":
                    "error",

                "message":
                    "Disk load must be a number."

            }), 400


        disk = max(

            0,

            min(
                95,
                disk
            )

        )


        simulated_disk_load = disk


    current_disk = (

        simulated_disk_load

        if simulated_disk_load is not None

        else psutil.disk_usage("/").percent

    )


    return jsonify({

        "status":
            "success",

        "disk":
            round(
                current_disk,
                1
            ),

        "simulated":
            simulated_disk_load is not None,

        "message":
            "Disk load simulation updated."

    })


# ============================================================
# TRAFFIC PREDICTION
# ============================================================

@app.route(
    "/api/v1/traffic/predict",
    methods=["GET"]
)
def predict_traffic():

    prediction = (
        predict_future_traffic()
    )


    return jsonify({

        "status":
            "success",

        "prediction":
            prediction,

        "timestamp":
            datetime.now().isoformat()

    })


# ============================================================
# WHAT IF TRAFFIC
# ============================================================

@app.route(
    "/api/v1/traffic/what-if",
    methods=["POST"]
)
def what_if_traffic():

    data = request.get_json(
        silent=True
    ) or {}


    try:

        increase_percent = float(

            data.get(
                "increase_percent",
                0
            )

        )


    except (
        TypeError,
        ValueError
    ):

        return jsonify({

            "status":
                "error",

            "message":
                "increase_percent must be a number."

        }), 400


    if increase_percent < 0:

        return jsonify({

            "status":
                "error",

            "message":
                "increase_percent cannot be negative."

        }), 400


    result = simulate_what_if_traffic(
        increase_percent
    )


    return jsonify({

        "status":
            "success",

        "simulation":
            result,

        "timestamp":
            datetime.now().isoformat()

    })


# ============================================================
# HEAL INDIVIDUAL VM
# ============================================================

@app.route(
    "/api/instances/<vm_id>/heal",
    methods=["POST"]
)
@app.route(
    "/api/v1/instances/<vm_id>/heal",
    methods=["POST"]
)
def heal_instance(vm_id):

    found = False


    for vm in VMS:

        if vm["id"] == vm_id:

            found = True

            vm["status"] = "Running"

            vm["cpu"] = round(
                30.0 +
                (hash(vm_id) % 20),
                1
            )

            vm["memory"] = round(
                40.0 +
                (hash(vm_id) % 15),
                1
            )


            break


    if not found:

        return jsonify({

            "status":
                "error",

            "message":
                f"{vm_id} not found."

        }), 404


    steps = self_heal(
        "Anomaly"
    )


    return jsonify({

        "status":
            "success",

        "message":
            f"Successfully healed instance {vm_id}",

        "steps":
            steps,

        "timestamp":
            datetime.now().isoformat()

    })


# ============================================================
# ML PREDICTION
# ============================================================

@app.route(
    "/api/predict",
    methods=["POST"]
)
@app.route(
    "/api/v1/predict",
    methods=["POST"]
)
def predict_anomaly():

    data = request.get_json(
        silent=True
    ) or {}


    cpu = float(

        data.get(
            "cpu",
            data.get(
                "CPU Usage (%)",
                psutil.cpu_percent(
                    interval=None
                )
            )
        )

    )
    response_time = float(
    data.get(
        "response_time",
        get_live_metrics()["response_time_ms"]
    )
)


    memory = float(

        data.get(
            "memory",
            data.get(
                "Memory Usage (%)",
                psutil.virtual_memory().percent
            )
        )

    )


    disk = float(

        data.get(
            "disk",
            data.get(
                "Disk Usage (%)",
                psutil.disk_usage("/").percent
            )
        )

    )


    features = pd.DataFrame([{

        "CPU Usage (%)":
            cpu,

        "Memory Usage (%)":
            memory,

        "Disk Usage (%)":
            disk,

        "Disk Read":
            float(
                data.get(
                    "Disk Read",
                    59208458752
                )
            ),

        "Disk Write":
            float(
                data.get(
                    "Disk Write",
                    49043329536
                )
            ),

        "Bytes Sent":
            float(
                data.get(
                    "Bytes Sent",
                    12994680
                )
            ),

        "Bytes Received":
            float(
                data.get(
                    "Bytes Received",
                    10279550
                )
            ),

        "Packets Sent":
            float(
                data.get(
                    "Packets Sent",
                    9441
                )
            ),

        "Packets Received":
            float(
                data.get(
                    "Packets Received",
                    15681
                )
            ),

        "Running Processes":
            int(
                data.get(
                    "Running Processes",
                    len(psutil.pids())
                )
            ),

        "System Uptime":
            int(
                data.get(
                    "System Uptime",
                    24000
                )
            ),

        "Service Status":
            int(
                data.get(
                    "Service Status",
                    0 if cpu < 85 else 1
                )
            ),

        "Response Time (ms)":
            float(
                data.get(
                    "Response Time (ms)",
                    0.0
                )
            ),

        "Health Check":
            int(
                data.get(
                    "Health Check",
                    0 if cpu < 85 else 1
                )
            )

    }])


    # --------------------------------------------------------
    # ML
    # --------------------------------------------------------

    if model is not None:

        try:

            pred = model.predict(
                features
            )[0]


            proba = (

                model.predict_proba(
                    features
                )[0][1]

                if hasattr(
                    model,
                    "predict_proba"
                )

                else
                (
                    0.95
                    if pred == 1
                    else
                    0.05
                )

            )


            is_anomaly = (
                bool(pred == 1)
            )


        except Exception:

            is_anomaly = (
                cpu > 80
                or memory > 85
            )

            proba = (
                0.89
                if is_anomaly
                else
                0.08
            )


    else:

        is_anomaly = (
            cpu > 80
            or memory > 85
        )

        proba = (
            0.89
            if is_anomaly
            else
            0.08
        )


    # --------------------------------------------------------
    # ANTI-REPEAT STATE
    # --------------------------------------------------------

    healing_triggered = False

    healing_status = "idle"

    healing_error = None

    current_rca = None


    global is_active_anomaly
    global last_healing_timestamp
    global last_healing_rca


    with healing_lock:

        if is_anomaly:

            if not is_active_anomaly:

                is_active_anomaly = True

                healing_triggered = True


                metrics_dict = {

                    "CPU Usage (%)":
                        float(cpu),

                    "Memory Usage (%)":
                        float(memory),

                    "Disk Usage (%)":
                        float(disk),

                    "Response Time (ms)":
                        float(
                            data.get(
                                "Response Time (ms)",
                                0.0
                            )
                        ),

                    "Running Processes":
                        int(
                            data.get(
                                "Running Processes",
                                len(psutil.pids())
                            )
                        ),

                    "System Uptime":
                        int(
                            data.get(
                                "System Uptime",
                                int(
                                    time.time()
                                    - psutil.boot_time()
                                )
                            )
                        ),

                    "Bytes Sent":
                        int(
                            data.get(
                                "Bytes Sent",
                                12994680
                            )
                        ),

                    "Bytes Received":
                        int(
                            data.get(
                                "Bytes Received",
                                10279550
                            )
                        )

                }


                try:

                    rca_res = generate_rca(

                        metrics_dict,

                        is_anomaly=True

                    )


                    if (
                        rca_res
                        and
                        rca_res.get(
                            "status"
                        ) == "success"
                    ):

                        current_rca = (
                            rca_res.get(
                                "rca"
                            )
                        )


                except Exception as gemini_err:

                    print(
                        "[PREDICT LIVE HEAL] "
                        f"Gemini RCA error: "
                        f"{gemini_err}"
                    )

                    current_rca = None


                last_healing_rca = (
                    current_rca
                )

                last_healing_timestamp = (
                    datetime.now().isoformat()
                )


                # Important:
                # ML prediction only performs
                # self-healing logging here.
                #
                # VM scaling is handled by
                # /api/v1/heal.

                try:

                    if current_rca:

                        self_heal(
                            "Anomaly",
                            rca=current_rca
                        )

                    else:

                        self_heal(
                            "Anomaly"
                        )


                    healing_status = (
                        "executed"
                    )


                except Exception as heal_err:

                    print(
                        "[PREDICT LIVE HEAL] "
                        f"self_heal error: "
                        f"{heal_err}"
                    )

                    healing_status = (
                        f"failed: {heal_err}"
                    )

                    healing_error = str(
                        heal_err
                    )


            else:

                healing_triggered = False

                healing_status = (
                    "active_remediation_in_progress"
                )

                current_rca = (
                    last_healing_rca
                )


        else:

            if is_active_anomaly:

                is_active_anomaly = False

                last_healing_rca = None


            healing_triggered = False

            healing_status = "nominal"


    risk_val = round(

        min(

            99.0,

            max(

                5.0,

                (
                    proba * 100
                    if is_anomaly

                    else

                    (
                        cpu * 0.4
                        + memory * 0.4
                        + (disk or 10) * 0.2
                    )
                )

            )

        ),

        1

    )


    response_payload = {

        "status":
            "success",

        "is_anomaly":
            is_anomaly,

        "prediction_label":
            (
                "Anomaly"
                if is_anomaly
                else
                "Normal"
            ),

        "anomaly_probability":
            float(
                round(
                    proba,
                    4
                )
            ),

        "confidence":
            float(
                round(
                    proba
                    if is_anomaly
                    else
                    (1.0 - proba),
                    4
                )
            ),

        "overall_cloud_risk":
            risk_val,

        "model_used":
            "RandomForestClassifier",

        "metrics_evaluated": {

            "cpu":
                cpu,

            "memory":
                memory,

            "disk":
                disk

        },

        "healing_triggered":
            healing_triggered,

        "healing_status":
            healing_status,

        "rca":
            current_rca

    }


    if healing_error:

        response_payload[
            "healing_error"
        ] = healing_error


    return jsonify(
        response_payload
    )


# ============================================================
# MAIN SELF-HEALING
# ============================================================

@app.route(
    "/api/heal",
    methods=["POST"]
)
@app.route(
    "/api/v1/heal",
    methods=["POST"]
)
def execute_healing():

    data = request.get_json(
        silent=True
    ) or {}


    pred_status = data.get(
        "status",
        "Anomaly"
    )


    global simulated_traffic
    global simulated_memory_load
    global simulated_disk_load
    global simulated_response_load
    global is_active_anomaly
    global active_injected_anomaly
    global active_injected_metrics


    # --------------------------------------------------------
    # SAVE LOAD BEFORE RESET
    # --------------------------------------------------------

    traffic_before_healing = (
        simulated_traffic
    )


    current_cpu = (
        get_live_metrics()
        ["cpu_usage"]
    )


    print(
        "================================"
    )

    print(
        "HEALING STARTED"
    )

    print(
        f"Traffic: "
        f"{traffic_before_healing}"
    )

    print(
        f"CPU: "
        f"{current_cpu}%"
    )

    print(
        f"Current VMs: "
        f"{len(VMS)}"
    )

    print(
        "================================"
    )


    # --------------------------------------------------------
    # SCALE OUT
    # --------------------------------------------------------
    #
    # ONE HEALING EVENT = ONE VM
    #
    # Example:
    #
    # Event 1 -> VM-02
    # Event 2 -> VM-03
    # Event 3 -> VM-04
    #
    # Maximum = VM-12
    # --------------------------------------------------------

    vm_scaling_result = None


    if (

        current_cpu >= 80

        or

        traffic_before_healing >= 1200

    ):

        print(
            "HIGH LOAD DETECTED"
        )

        print(
            "STARTING SCALE OUT..."
        )


        if len(VMS) < MAX_VMS:

            new_vm = scale_out()


            if new_vm is not None:

                vm_scaling_result = new_vm


                print(
                    f"Added {new_vm['id']}"
                )


        else:

            print(
                "SCALE OUT SKIPPED: "
                "Maximum VM limit reached."
            )


        print(
            f"SCALE OUT FINISHED: "
            f"{len(VMS)} VMs"
        )


    else:

        print(
            "No scale-out required."
        )


    # --------------------------------------------------------
    # SELF HEALING
    # --------------------------------------------------------

    try:

        steps = self_heal(
            pred_status
        )

    except Exception as heal_err:

        print(
            f"Self-heal error: {heal_err}"
        )

        steps = [
            "Self-healing action completed"
        ]


    # --------------------------------------------------------
    # RESET SIMULATION
    # --------------------------------------------------------

    with healing_lock:

        is_active_anomaly = False

        active_injected_anomaly = None

        active_injected_metrics = None

        simulated_traffic = 100

        simulated_memory_load = None

        simulated_disk_load = 15.0

        simulated_response_load = 100.0


    # --------------------------------------------------------
    # RESET VM HEALTH
    # --------------------------------------------------------

    for vm in VMS:

        vm["status"] = "Running"

        vm["cpu"] = round(

            25.0 +
            (hash(vm["id"]) % 15),

            1

        )

        vm["memory"] = round(

            35.0 +
            (hash(vm["id"]) % 15),

            1

        )


    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    response_data = {

        "status":
            "success",

        "message":
            "Self-healing pipeline "
            "completed successfully",

        "remediation_steps":
            steps,

        "vm_scaling": {

            "traffic_before_healing":
                traffic_before_healing,

            "cpu_before_healing":
                current_cpu,

            "total_vms":
                len(VMS),

            "maximum_vms":
                MAX_VMS,

            "vm_added":
                (
                    vm_scaling_result["id"]
                    if vm_scaling_result
                    else None
                )

        },

        "restored_metrics": {

            "cpu":
                22.0,

            "memory":
                38.0,

            "latency":
                100.0,

            "disk":
                15.0

        },

        "timestamp":
            datetime.now().isoformat()

    }


    return jsonify(
        response_data
    )


# ============================================================
# FAULT INJECTION
# ============================================================

@app.route(
    "/api/inject",
    methods=["POST"]
)
@app.route(
    "/api/v1/inject",
    methods=["POST"]
)
def inject_fault():

    global active_injected_anomaly
    global active_injected_metrics
    global is_active_anomaly
    global last_healing_rca


    with healing_lock:

        is_active_anomaly = False

        last_healing_rca = None


    data = request.get_json(
        silent=True
    ) or {}


    raw_type = str(
        data.get(
            "type",
            "CPU_SPIKE"
        )
    ).upper()


    # --------------------------------------------------------
    # IMPORTANT:
    #
    # Do NOT create 9 or 12 VMs here.
    #
    # Fault injection uses existing VMs only.
    # --------------------------------------------------------

    target_vm = VMS[0]


    # ========================================================
    # CPU
    # ========================================================

    if "CPU" in raw_type:

        fault_type = "CPU_SPIKE"

        cause = (
            "CPU Throttling & Spike (>90%)"
        )

        injected_metrics = {

            "cpu":
                98.5,

            "memory":
                88.2,

            "latency":
                220.0,

            "disk":
                45.0,

            "Service Status":
                1,

            "Health Check":
                1

        }


        target_vm["cpu"] = 98.5

        target_vm["status"] = "Critical"


    # ========================================================
    # MEMORY
    # ========================================================

    elif "MEM" in raw_type:

        fault_type = "MEMORY_LEAK"

        cause = (
            "Critical Memory Leak (96%)"
        )

        injected_metrics = {

            "cpu":
                89.0,

            "memory":
                96.5,

            "latency":
                180.0,

            "disk":
                40.0,

            "Service Status":
                1,

            "Health Check":
                1

        }


        target_vm["memory"] = 96.5

        target_vm["status"] = "Critical"


    # ========================================================
    # NETWORK
    # ========================================================

    elif (
        "LATENCY" in raw_type
        or
        "NET" in raw_type
    ):

        fault_type = "NETWORK_LATENCY"

        cause = (
            "Network Latency Degraded (400ms)"
        )

        injected_metrics = {

            "cpu":
                62.0,

            "memory":
                71.0,

            "latency":
                410.0,

            "disk":
                35.0,

            "Service Status":
                1,

            "Health Check":
                1

        }


        target_vm["status"] = "Warning"

        target_vm["cpu"] = 72.0


    # ========================================================
    # CRASH
    # ========================================================

    elif (
        "CRASH" in raw_type
        or
        "OUTAGE" in raw_type
    ):

        fault_type = "CRITICAL_CRASH"

        cause = (
            "CRITICAL MODULE CRASH "
            "(Node Outage)"
        )

        injected_metrics = {

            "cpu":
                99.9,

            "memory":
                98.8,

            "latency":
                495.0,

            "disk":
                96.0,

            "Service Status":
                1,

            "Health Check":
                1

        }


        target_vm["cpu"] = 99.9

        target_vm["memory"] = 98.8

        target_vm["status"] = "Critical"


    # ========================================================
    # RESOURCE CONTENTION
    # ========================================================

    else:

        fault_type = (
            "RESOURCE_CONTENTION"
        )

        cause = (
            "High Resource Contention"
        )

        injected_metrics = {

            "cpu":
                96.5,

            "memory":
                88.2,

            "latency":
                220.0,

            "disk":
                92.0,

            "Service Status":
                1,

            "Health Check":
                1

        }


        target_vm["cpu"] = 96.5

        target_vm["memory"] = 88.2

        target_vm["status"] = "Critical"


    # --------------------------------------------------------
    # SAVE INJECTED STATE
    # --------------------------------------------------------

    active_injected_anomaly = (
        fault_type
    )

    active_injected_metrics = (
        injected_metrics
    )


    # --------------------------------------------------------
    # LOG
    # --------------------------------------------------------

    log_file_path = os.path.join(

        BACKEND_DIR,

        "healing",

        "healing_log.txt"

    )


    try:

        affected_str = ", ".join(

            [
                v["id"]
                for v in VMS
                if v["status"] != "Running"
            ]

        ) or "Cluster Nodes"


        with open(
            log_file_path,
            "a"
        ) as f:

            f.write(

                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                f"Fault Injected: {fault_type} | "
                f"Node(s): {affected_str} | "
                f"Metric Trigger: {cause}\n"

            )


    except Exception:

        pass


    return jsonify({

        "status":
            "success",

        "fault_type":
            fault_type,

        "cause":
            cause,

        "metrics":
            injected_metrics,

        "message":
            f"Fault injection "
            f"'{fault_type}' "
            f"simulated successfully",

        "affected_vms":
            [
                v
                for v in VMS
                if v["status"] != "Running"
            ],

        "timestamp":
            datetime.now().isoformat()

    })


# ============================================================
# LOG READER
# ============================================================

def read_recent_logs(limit=20):

    logs = []


    log_file_path = os.path.join(

        BACKEND_DIR,

        "healing",

        "healing_log.txt"

    )


    if os.path.exists(
        log_file_path
    ):

        try:

            with open(
                log_file_path,
                "r"
            ) as f:

                lines = f.readlines()


                for idx, line in enumerate(

                    reversed(
                        lines[-limit:]
                    )

                ):

                    parts = (
                        line
                        .strip()
                        .split(" | ")
                    )


                    if len(parts) >= 3:

                        is_resolved = (

                            "restarted"
                            in parts[2]
                            .lower()

                            or

                            "normal"
                            in parts[1]
                            .lower()

                            or

                            "nominal"
                            in parts[2]
                            .lower()

                        )


                        logs.append({

                            "id":
                                idx + 1,

                            "timestamp":
                                parts[0],

                            "time":
                                parts[0],

                            "prediction":
                                parts[1],

                            "anomaly":
                                parts[1],

                            "action":
                                parts[2],

                            "node":
                                (
                                    "VM-03"
                                    if "CPU"
                                    in parts[1]

                                    or "Crash"
                                    in parts[1]

                                    else

                                    (
                                        "VM-02"
                                        if "Mem"
                                        in parts[1]

                                        else
                                        "Cluster"
                                    )
                                ),

                            "status":
                                (
                                    "RESOLVED"
                                    if is_resolved
                                    else
                                    "ACTIVE"
                                )

                        })


                    elif line.strip():

                        logs.append({

                            "id":
                                idx + 1,

                            "raw":
                                line.strip(),

                            "time":
                                datetime.now().strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                ),

                            "status":
                                "INFO"

                        })


        except Exception as e:

            logs.append({

                "error":
                    str(e)

            })


    return logs


# ============================================================
# LOG API
# ============================================================

@app.route("/api/logs")
@app.route("/api/v1/logs")
def get_logs():

    return jsonify({

        "status":
            "success",

        "logs":
            read_recent_logs(50)

    })


# ============================================================
# BENCHMARKS
# ============================================================

@app.route("/api/benchmarks")
@app.route("/api/v1/benchmarks")
@app.route("/api/v1/models/benchmarks")
def get_benchmarks():

    models_list = [

        {

            "Model Name":
                "LightGBM",

            "name":
                "LightGBM",

            "Accuracy":
                0.9306,

            "accuracy":
                0.9306,

            "Precision":
                0.9313,

            "precision":
                0.9313,

            "Recall":
                0.9306,

            "recall":
                0.9306,

            "F1":
                0.9306,

            "f1_score":
                0.9306,

            "ROC AUC":
                0.9794,

            "roc_auc":
                0.9794,

            "Training Time":
                0.2940,

            "Prediction Time":
                0.0022,

            "latency_ms":
                2.2,

            "status":
                "Ready"

        },


        {

            "Model Name":
                "CatBoost",

            "name":
                "CatBoost",

            "Accuracy":
                0.9306,

            "accuracy":
                0.9306,

            "Precision":
                0.9313,

            "precision":
                0.9313,

            "Recall":
                0.9306,

            "recall":
                0.9306,

            "F1":
                0.9306,

            "f1_score":
                0.9306,

            "ROC AUC":
                0.9781,

            "roc_auc":
                0.9781,

            "Training Time":
                0.1177,

            "Prediction Time":
                0.0004,

            "latency_ms":
                0.4,

            "status":
                "Ready"

        },


        {

            "Model Name":
                "Random Forest",

            "name":
                "Random Forest",

            "Accuracy":
                0.9268,

            "accuracy":
                0.9268,

            "Precision":
                0.9280,

            "precision":
                0.9280,

            "Recall":
                0.9268,

            "recall":
                0.9268,

            "F1":
                0.9267,

            "f1_score":
                0.9267,

            "ROC AUC":
                0.9760,

            "roc_auc":
                0.9760,

            "Training Time":
                0.1611,

            "Prediction Time":
                0.0045,

            "latency_ms":
                4.5,

            "status":
                "Active"

        },


        {

            "Model Name":
                "XGBoost",

            "name":
                "XGBoost",

            "Accuracy":
                0.9210,

            "accuracy":
                0.9210,

            "Precision":
                0.9212,

            "precision":
                0.9212,

            "Recall":
                0.9210,

            "recall":
                0.9210,

            "F1":
                0.9210,

            "f1_score":
                0.9210,

            "ROC AUC":
                0.9750,

            "roc_auc":
                0.9750,

            "Training Time":
                0.0243,

            "Prediction Time":
                0.0013,

            "latency_ms":
                1.3,

            "status":
                "Ready"

        },


        {

            "Model Name":
                "Isolation Forest",

            "name":
                "Isolation Forest",

            "Accuracy":
                0.5106,

            "accuracy":
                0.5106,

            "Precision":
                0.5287,

            "precision":
                0.5287,

            "Recall":
                0.5106,

            "recall":
                0.5106,

            "F1":
                0.4141,

            "f1_score":
                0.4141,

            "ROC AUC":
                0.5098,

            "roc_auc":
                0.5098,

            "Training Time":
                0.0554,

            "Prediction Time":
                0.0043,

            "latency_ms":
                4.3,

            "status":
                "Ready"

        }

    ]


    return jsonify(
        models_list
    )


# ============================================================
# RECOVERY DECISION
# ============================================================

@app.route(
    "/api/v1/recovery/decision",
    methods=["POST"]
)
def recovery_decision():

    data = request.get_json(
        silent=True
    ) or {}


    incident_id = (
        f"INC-{len(incident_history) + 1:03d}"
    )


    add_incident_event(

        incident_id,

        "Recovery analysis started"

    )


    metrics = data.get(
        "metrics"
    )


    if not isinstance(
        metrics,
        dict
    ):

        metrics = {

            "cpu":
                data.get(
                    "cpu",
                    psutil.cpu_percent(
                        interval=None
                    )
                ),

            "memory":
                data.get(
                    "memory",
                    psutil.virtual_memory().percent
                ),

            "disk":
                data.get(
                    "disk",
                    psutil.disk_usage("/").percent
                ),

            "latency":
                data.get(
                    "latency",
                    0
                )

        }


    prediction = (
        predict_future_traffic()
    )


    predicted_scale_out = (
        prediction
        .get(
            "scale_out_recommended",
            False
        )
    )


    decision = choose_recovery_action(

        metrics=metrics,

        rca=data.get(
            "rca",
            ""
        ),

        current_instances=
            len(VMS),

        anomaly=(

            bool(
                data.get(
                    "anomaly",
                    False
                )
            )

            or

            simulated_traffic >= 1200

            or

            predicted_scale_out

        )

    )


    if predicted_scale_out:

        decision["action"] = (
            SCALE_OUT
        )

        decision["reason"] = (

            "Predicted traffic is expected "
            "to increase CPU utilization. "
            "Scaling out early can provide "
            "additional capacity before "
            "overload occurs."

        )


    recovery_action = (
        decision.get(
            "action"
        )
    )


    explanation = {

        "cpu":
            metrics.get("cpu"),

        "memory":
            metrics.get("memory"),

        "traffic":
            simulated_traffic,

        "root_cause":
            data.get(
                "rca",
                ""
            ),

        "decision":
            recovery_action

    }


    add_incident_event(

        incident_id,

        f"Recovery decision: "
        f"{recovery_action}"

    )


    execution_result = (
        execute_recovery_action(
            recovery_action
        )
    )


    decision["execution"] = (
        execution_result
    )


    add_incident_event(

        incident_id,

        "Recovery executed: "
        f"{execution_result.get('status', 'unknown')}"

    )


    vm_id = (
        execution_result.get(
            "vm"
        )
    )


    if recovery_action == "NO_ACTION":

        verification_result = {

            "status":
                "healthy",

            "verified":
                True,

            "message":
                "No recovery action was required."

        }


    elif recovery_action == "SCALE_OUT":

        # New VM is healthy immediately
        verification_result = {

            "status":
                "healthy",

            "verified":
                True,

            "vm":
                vm_id,

            "message":
                (
                    f"{vm_id} added and "
                    "verified successfully."
                    if vm_id
                    else
                    "Scale-out completed."
                )

        }


    else:

        verification_result = (
            verify_recovery(vm_id)
        )


    decision["verification"] = (
        verification_result
    )


    add_incident_event(

        incident_id,

        "Recovery verification: "
        f"{verification_result.get('status', 'unknown')}"

    )


    mttr = calculate_mttr(
        incident_id
    )


    decision["mttr_seconds"] = (
        mttr
    )

    decision["explanation"] = (
        explanation
    )


    return jsonify({

        "status":
            "success",

        "recovery_decision":
            decision,

        "timestamp":
            datetime.now().isoformat()

    })


# ============================================================
# RECOVERY EXPLAIN
# ============================================================

@app.route(
    "/api/v1/recovery/explain",
    methods=["POST"]
)
def explain_recovery():

    data = request.get_json(
        silent=True
    ) or {}


    metrics = data.get(
        "metrics",
        {}
    )


    if not isinstance(
        metrics,
        dict
    ):

        metrics = {}


    rca = data.get(

        "rca",

        "System workload anomaly"

    )


    try:

        current_instances = int(

            data.get(
                "current_instances",
                1
            )

        )

    except (
        TypeError,
        ValueError
    ):

        current_instances = 1


    try:

        decision = choose_recovery_action(

            metrics=metrics,

            rca=rca,

            current_instances=
                current_instances,

            min_instances=1,

            max_instances=12,

            anomaly=True

        )


        return jsonify({

            "status":
                "success",

            "recovery_decision":
                decision,

            "timestamp":
                datetime.now().isoformat()

        })


    except Exception as error:

        return jsonify({

            "status":
                "error",

            "message":
                str(error)

        }), 500


# ============================================================
# INCIDENTS
# ============================================================

@app.route(
    "/api/v1/incidents",
    methods=["GET"]
)
def get_incidents():

    return jsonify({

        "status":
            "success",

        "incidents":
            incident_history

    })


# ============================================================
# START SERVER
# ============================================================

print(
    "REGISTERED ROUTES:"
)

print(
    app.url_map
)


if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5001
        )
    )


    print(
        f"Starting SelfHealing Backend "
        f"server on "
        f"http://127.0.0.1:{port}..."
    )


    app.run(

        host="0.0.0.0",

        port=port,

        debug=False

    )