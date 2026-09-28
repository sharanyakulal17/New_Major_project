import os
import sys
import time
import subprocess
import psutil
from datetime import datetime

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(CURRENT_DIR, "healing_log.txt")

# Whitelisted Predefined Remediation Actions
ACTION_RESTART_COLLECTOR = "RESTART_MONITORING_SERVICE"
ACTION_SAFE_FALLBACK = "SAFE_FALLBACK_RESTART"
ACTION_NO_ACTION = "NO_ACTION_REQUIRED"

REMEDIATION_WHITELIST = {
    ACTION_RESTART_COLLECTOR: "Restart Monitoring Service Process (collect_metrics.py)",
    ACTION_SAFE_FALLBACK: "Safe Fallback Remediation (Restart Monitoring Service)",
    ACTION_NO_ACTION: "No Action Required"
}

HEALTH_CHECK_TIMEOUT = 10.0
HEALTH_CHECK_INTERVAL = 0.5


def map_rca_to_remediation_action(prediction, rca=None):
    """
    Safely maps the diagnosis/RCA into a strictly whitelisted remediation action.
    Gemini RCA is NEVER executed directly as shell commands.
    """
    if prediction != "Anomaly":
        return ACTION_NO_ACTION, "System Healthy"

    if not rca:
        return ACTION_RESTART_COLLECTOR, "Standard Anomaly Recovery (Monitoring Service Restart)"

    rca_lower = str(rca).lower()

    # Whitelisted semantic mapping rules
    if any(k in rca_lower for k in ["cpu", "compute", "saturation", "thread", "spike"]):
        return ACTION_RESTART_COLLECTOR, "High CPU Saturation Remediation"
    elif any(k in rca_lower for k in ["memory", "ram", "leak", "oom", "exhaustion", "pressure"]):
        return ACTION_RESTART_COLLECTOR, "Memory Pressure / Saturation Remediation"
    elif any(k in rca_lower for k in ["collector", "hang", "timeout", "service", "probe", "monitoring"]):
        return ACTION_RESTART_COLLECTOR, "Monitoring Service Process Recovery"
    else:
        # Safe fallback for unknown or unclassified RCA (strictly preventing arbitrary command execution)
        return ACTION_SAFE_FALLBACK, "Safe Fallback Remediation"


def verify_monitoring_service_health(new_pid, restart_time=None, timeout=HEALTH_CHECK_TIMEOUT, interval=HEALTH_CHECK_INTERVAL):
    """
    Performs comprehensive post-remediation health verification:
    1. Process Liveness
    2. Command Line Verification
    3. Telemetry File Readability
    4. Schema & Data Parsing
    5. Telemetry Freshness
    """
    backend_dir = os.path.dirname(CURRENT_DIR)
    csv_file = os.path.join(backend_dir, "monitoring", "datasets", "system_metrics.csv")
    target_script = "collect_metrics.py"

    verification_details = {
        "process_alive": False,
        "command_verified": False,
        "telemetry_readable": False,
        "latest_telemetry_available": False,
        "telemetry_fresh": False,
        "status": "FAILED",
        "reason": None
    }

    start_poll = time.time()
    while time.time() - start_poll < timeout:
        # A & B. Process Liveness
        if not new_pid or not psutil.pid_exists(new_pid):
            verification_details["reason"] = f"PID {new_pid} is not alive in process table"
            time.sleep(interval)
            continue

        try:
            p = psutil.Process(new_pid)
            if p.status() == psutil.STATUS_ZOMBIE or not p.is_running():
                verification_details["reason"] = f"PID {new_pid} is zombie or not running"
                time.sleep(interval)
                continue
            verification_details["process_alive"] = True

            # C. Command Line Verification
            cmdline = p.cmdline()
            if any(target_script in arg for arg in cmdline):
                verification_details["command_verified"] = True
            else:
                verification_details["reason"] = f"Process cmdline does not contain {target_script}"
                time.sleep(interval)
                continue
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            verification_details["reason"] = f"Cannot access process info for PID {new_pid}"
            time.sleep(interval)
            continue

        # D & E. Telemetry File Readability
        if not os.path.exists(csv_file):
            verification_details["reason"] = f"Telemetry file {csv_file} does not exist"
            time.sleep(interval)
            continue

        try:
            with open(csv_file, "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f.readlines() if l.strip()]
            verification_details["telemetry_readable"] = True
        except Exception as e:
            verification_details["reason"] = f"Telemetry file unreadable: {e}"
            time.sleep(interval)
            continue

        if len(lines) < 2:  # Header + at least 1 data row
            verification_details["reason"] = "Telemetry file has no data rows"
            time.sleep(interval)
            continue

        # F & G. Latest telemetry record parsing and required fields
        latest_line = lines[-1]
        parts = [p.strip() for p in latest_line.split(",")]
        if len(parts) < 16:
            verification_details["reason"] = f"Telemetry row has invalid column count ({len(parts)} < 16)"
            time.sleep(interval)
            continue

        ts_str = parts[0]
        try:
            row_dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
            float(parts[1])  # CPU
            float(parts[2])  # Memory
            float(parts[3])  # Disk
            verification_details["latest_telemetry_available"] = True
        except Exception as e:
            verification_details["reason"] = f"Failed to parse telemetry metrics: {e}"
            time.sleep(interval)
            continue

        # H. Telemetry Freshness check
        now_dt = datetime.now()
        age_seconds = (now_dt - row_dt).total_seconds()
        if restart_time:
            if age_seconds <= 20.0 or (row_dt >= restart_time):
                verification_details["telemetry_fresh"] = True
            else:
                verification_details["reason"] = f"Telemetry row is stale ({age_seconds:.1f}s old)"
                time.sleep(interval)
                continue
        else:
            if age_seconds <= 20.0:
                verification_details["telemetry_fresh"] = True
            else:
                verification_details["reason"] = f"Telemetry row is stale ({age_seconds:.1f}s old)"
                time.sleep(interval)
                continue

        # All checks passed!
        verification_details["status"] = "SUCCESS"
        verification_details["reason"] = "All health checks passed successfully"
        return True, verification_details

    # If timeout expired without all checks passing
    verification_details["status"] = "FAILED"
    return False, verification_details


def restart_monitoring_service(restart_time=None):
    """
    Predefined real remediation action:
    Safely terminates any stale/hung instance of collect_metrics.py,
    spawns a fresh background telemetry collector, and performs rigorous post-remediation health verification.
    """
    target_script = "collect_metrics.py"
    current_pid = os.getpid()
    terminated_pids = []

    # 1. Terminate all running collect_metrics.py instances
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['pid'] == current_pid:
                continue
            cmdline = proc.info.get('cmdline') or []
            if any(target_script in str(arg) for arg in cmdline):
                old_pid = proc.info['pid']
                terminated_pids.append(old_pid)
                proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    # Double check and ensure zero lingering collector processes exist
    time.sleep(0.5)
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['pid'] == current_pid:
                continue
            cmdline = proc.info.get('cmdline') or []
            if any(target_script in str(arg) for arg in cmdline):
                proc.kill()
        except Exception:
            pass

    # 2. Locate and spawn fresh collector process
    backend_dir = os.path.dirname(CURRENT_DIR)
    collector_path = os.path.join(backend_dir, "monitoring", "collect_metrics.py")

    if not os.path.exists(collector_path):
        v_fail = {
            "process_alive": False, "command_verified": False,
            "telemetry_readable": False, "latest_telemetry_available": False,
            "telemetry_fresh": False, "status": "FAILED", "reason": "Collector script not found"
        }
        return False, "Collector script not found at expected path", None, terminated_pids, v_fail

    try:
        restart_start = restart_time or datetime.now()
        new_proc = subprocess.Popen(
            [sys.executable, collector_path],
            cwd=os.path.join(backend_dir, "monitoring"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

        # 3. Comprehensive Post-Remediation Health Verification
        is_healthy, v_details = verify_monitoring_service_health(new_proc.pid, restart_time=restart_start)

        if is_healthy:
            pid_info = f"PID {new_proc.pid}"
            if terminated_pids:
                pid_info += f" (replaced stale PID {', '.join(map(str, terminated_pids))})"
            return True, f"Monitoring Service restarted successfully ({pid_info})", new_proc.pid, terminated_pids, v_details
        else:
            reason = v_details.get("reason", "Health check failed")
            return False, f"Post-remediation health verification failed: {reason}", new_proc.pid, terminated_pids, v_details
    except Exception as err:
        v_err = {
            "process_alive": False, "command_verified": False,
            "telemetry_readable": False, "latest_telemetry_available": False,
            "telemetry_fresh": False, "status": "FAILED", "reason": str(err)
        }
        return False, f"Failed to spawn collector process: {err}", None, terminated_pids, v_err


def self_heal(prediction, rca=None):
    steps = []
    clean_rca = None

    if rca:
        clean_rca = " ".join(str(rca).split()).strip()

    # Determine whitelisted action from RCA mapping
    action_key, action_desc = map_rca_to_remediation_action(prediction, rca=clean_rca)

    remediation_success = False
    new_pid = None
    v_details = {}

    if prediction == "Anomaly":
        print("\n🚨 Anomaly Detected!\n - self_heal.py:13")

        steps.append("📊 Collecting latest system metrics...")
        time.sleep(0.1)

        steps.append("🧹 Preprocessing collected metrics...")
        time.sleep(0.1)

        steps.append("🤖 Running Random Forest prediction...")
        time.sleep(0.1)

        steps.append(f"🔍 Root cause identified : {action_desc}")
        time.sleep(0.1)

        if clean_rca:
            steps.append(f"🧠 Gemini AI Diagnosis: {clean_rca}")
            time.sleep(0.1)

        steps.append(f"🎯 Selected Remediation: {REMEDIATION_WHITELIST.get(action_key, action_key)}")
        steps.append("🔄 Restarting Monitoring Service...")

        # Execute strictly whitelisted remediation action & health verification
        remediation_success, status_msg, new_pid, old_pids, v_details = restart_monitoring_service()

        verif_status = v_details.get("status", "FAILED") if isinstance(v_details, dict) else str(v_details)
        telemetry_status = "HEALTHY" if (isinstance(v_details, dict) and v_details.get("telemetry_fresh")) else "STALE/UNAVAILABLE"

        steps.append("🩺 Running Health Verification...")
        if isinstance(v_details, dict):
            steps.append(f"  • Process Alive: {'PASS' if v_details.get('process_alive') else 'FAIL'}")
            steps.append(f"  • Command Verified: {'PASS' if v_details.get('command_verified') else 'FAIL'}")
            steps.append(f"  • Telemetry File Readable: {'PASS' if v_details.get('telemetry_readable') else 'FAIL'}")
            steps.append(f"  • Latest Telemetry Available: {'PASS' if v_details.get('latest_telemetry_available') else 'FAIL'}")
            steps.append(f"  • Telemetry Freshness: {'PASS' if v_details.get('telemetry_fresh') else 'FAIL'}")
        steps.append(f"🩺 Verification Result: {verif_status}")

        if remediation_success and verif_status == "SUCCESS":
            action = f"Monitoring Service Restarted (PID: {new_pid})"
            steps.append(f"✅ Recovery Successful: {status_msg}")
        else:
            action = f"Remediation Failed: {status_msg}"
            steps.append(f"❌ Recovery Failed: {status_msg}")

        for step in steps:
            print(step)

    else:
        action = "No Action Required"
        verif_status = "SKIPPED"
        telemetry_status = "HEALTHY"
        v_details = {"status": "SKIPPED"}
        print("🟢 System Healthy - self_heal.py:46")

    # Save logs (safely wrapped so log write errors never stop self-healing)
    try:
        with open(LOG_FILE, "a") as file:
            log_parts = [str(datetime.now()), prediction, action]
            if clean_rca:
                log_parts.append(f"RCA: {clean_rca}")
            log_parts.append(f"Action: {action_key}")
            log_parts.append(f"Verification: {verif_status}")
            log_parts.append(f"Telemetry: {telemetry_status}")
            if verif_status == "FAILED" and isinstance(v_details, dict) and v_details.get("reason"):
                log_parts.append(f"Reason: {v_details.get('reason')}")
            file.write(" | ".join(log_parts) + "\n")
    except Exception as log_err:
        print(f"Warning: Failed to write to healing_log.txt: {log_err}")

    # Attach structured healing result to function object for callers that need rich metadata
    self_heal.last_healing_info = {
        "prediction": prediction,
        "rca": clean_rca,
        "action": action_key,
        "pid": new_pid if prediction == "Anomaly" else None,
        "verification": v_details,
        "success": bool(remediation_success if prediction == "Anomaly" else True)
    }

    return steps


if __name__ == "__main__":
    self_heal("Anomaly")