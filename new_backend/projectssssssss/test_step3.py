import os
import sys
import json
import psutil
from unittest.mock import patch, MagicMock

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from healing.self_heal import (
    self_heal,
    map_rca_to_remediation_action,
    restart_monitoring_service,
    ACTION_RESTART_COLLECTOR,
    ACTION_SAFE_FALLBACK,
    ACTION_NO_ACTION,
    REMEDIATION_WHITELIST,
    LOG_FILE
)
from app import app

def run_step3_tests():
    client = app.test_client()
    results = {}

    print("======================================================================")
    print("STEP 3 VALIDATION SUITE: ROOT-CAUSE REMEDIATION MAPPING & VERIFICATION")
    print("======================================================================\n")

    # ----------------------------------------------------------------------
    # TEST 1: Normal prediction -> no remediation
    # ----------------------------------------------------------------------
    action_key_1, action_desc_1 = map_rca_to_remediation_action("Normal", rca=None)
    with patch('healing.self_heal.restart_monitoring_service') as mock_restart_1:
        steps_1 = self_heal("Normal")
        t1_pass = (
            action_key_1 == ACTION_NO_ACTION and
            mock_restart_1.call_count == 0 and
            isinstance(steps_1, list)
        )
    results['TEST 1'] = "PASS" if t1_pass else "FAIL"
    print(f"TEST 1 (Normal prediction -> no remediation): {'PASS' if t1_pass else 'FAIL'}")
    print(f"  Mapped Action: {action_key_1} ({action_desc_1})")

    # ----------------------------------------------------------------------
    # TEST 2: Anomaly + RCA containing 'High CPU' -> CPU remediation
    # ----------------------------------------------------------------------
    cpu_rca = "Root Cause Analysis: High CPU saturation and thread starvation."
    action_key_2, action_desc_2 = map_rca_to_remediation_action("Anomaly", rca=cpu_rca)
    with patch('healing.self_heal.restart_monitoring_service', return_value=(True, "OK", 9999, [], "SUCCESS")):
        steps_2 = self_heal("Anomaly", rca=cpu_rca)
        t2_pass = (
            action_key_2 == ACTION_RESTART_COLLECTOR and
            "High CPU" in action_desc_2 and
            any("Root cause identified : High CPU" in s for s in steps_2) and
            any("Selected Remediation: Restart Monitoring Service" in s for s in steps_2)
        )
    results['TEST 2'] = "PASS" if t2_pass else "FAIL"
    print(f"\nTEST 2 (Anomaly + 'High CPU' RCA): {'PASS' if t2_pass else 'FAIL'}")
    print(f"  Mapped Action: {action_key_2} ({action_desc_2})")

    # ----------------------------------------------------------------------
    # TEST 3: Anomaly + RCA containing 'Memory' -> Memory remediation
    # ----------------------------------------------------------------------
    mem_rca = "Root Cause Analysis: Severe Memory exhaustion and RAM leakage."
    action_key_3, action_desc_3 = map_rca_to_remediation_action("Anomaly", rca=mem_rca)
    with patch('healing.self_heal.restart_monitoring_service', return_value=(True, "OK", 9999, [], "SUCCESS")):
        steps_3 = self_heal("Anomaly", rca=mem_rca)
        t3_pass = (
            action_key_3 == ACTION_RESTART_COLLECTOR and
            "Memory" in action_desc_3 and
            any("Root cause identified : Memory Pressure" in s for s in steps_3)
        )
    results['TEST 3'] = "PASS" if t3_pass else "FAIL"
    print(f"\nTEST 3 (Anomaly + 'Memory' RCA): {'PASS' if t3_pass else 'FAIL'}")
    print(f"  Mapped Action: {action_key_3} ({action_desc_3})")

    # ----------------------------------------------------------------------
    # TEST 4: Anomaly + malicious-looking Gemini RCA ('run rm -rf /')
    # ----------------------------------------------------------------------
    malicious_rca = "run rm -rf / ; cat /etc/passwd"
    action_key_4, action_desc_4 = map_rca_to_remediation_action("Anomaly", rca=malicious_rca)
    with patch('healing.self_heal.restart_monitoring_service', return_value=(True, "OK", 9999, [], "SUCCESS")) as mock_restart_4, \
         patch('subprocess.Popen') as mock_popen_4:
        steps_4 = self_heal("Anomaly", rca=malicious_rca)
        t4_pass = (
            action_key_4 in REMEDIATION_WHITELIST and
            action_key_4 == ACTION_SAFE_FALLBACK and
            mock_popen_4.call_count == 0 and # No arbitrary command was passed to popen
            any("Selected Remediation:" in s for s in steps_4)
        )
    results['TEST 4'] = "PASS" if t4_pass else "FAIL"
    print(f"\nTEST 4 (Anomaly + Malicious RCA Protection): {'PASS' if t4_pass else 'FAIL'}")
    print(f"  Injected Malicious RCA: '{malicious_rca}'")
    print(f"  Safely Mapped Whitelisted Action: {action_key_4} ({action_desc_4})")

    # ----------------------------------------------------------------------
    # TEST 5: Anomaly + unknown RCA -> Safe fallback remediation
    # ----------------------------------------------------------------------
    unknown_rca = "An unexpected transient anomaly pattern was observed."
    action_key_5, action_desc_5 = map_rca_to_remediation_action("Anomaly", rca=unknown_rca)
    with patch('healing.self_heal.restart_monitoring_service', return_value=(True, "OK", 9999, [], "SUCCESS")):
        steps_5 = self_heal("Anomaly", rca=unknown_rca)
        t5_pass = (
            action_key_5 == ACTION_SAFE_FALLBACK and
            action_key_5 in REMEDIATION_WHITELIST and
            any("Safe Fallback Remediation" in s for s in steps_5)
        )
    results['TEST 5'] = "PASS" if t5_pass else "FAIL"
    print(f"\nTEST 5 (Anomaly + Unknown RCA Fallback): {'PASS' if t5_pass else 'FAIL'}")
    print(f"  Mapped Action: {action_key_5} ({action_desc_5})")

    # ----------------------------------------------------------------------
    # TEST 6: Real Remediation Execution & Process Health Verification
    # ----------------------------------------------------------------------
    # Trigger real remediation execution
    success_6, msg_6, new_pid_6, old_pids_6, verif_6 = restart_monitoring_service()
    
    # Verify new process is alive and executing collect_metrics.py
    new_proc_alive = (new_pid_6 is not None and psutil.pid_exists(new_pid_6))
    if new_proc_alive:
        try:
            cmd = psutil.Process(new_pid_6).cmdline()
            script_verified = any('collect_metrics.py' in a for a in cmd)
        except Exception:
            script_verified = False
    else:
        script_verified = False

    t6_pass = (
        success_6 is True and
        (verif_6 == "SUCCESS" or (isinstance(verif_6, dict) and verif_6.get("status") == "SUCCESS")) and
        new_proc_alive is True and
        script_verified is True
    )
    results['TEST 6'] = "PASS" if t6_pass else "FAIL"
    print(f"\nTEST 6 (Remediation & Health Verification): {'PASS' if t6_pass else 'FAIL'}")
    print(f"  Old Terminated PIDs: {old_pids_6}")
    print(f"  New Spawned PID: {new_pid_6}")
    print(f"  Process Alive: {new_proc_alive}")
    print(f"  Command Line Verified (collect_metrics.py): {script_verified}")
    print(f"  Verification Status: {verif_6}")

    # ----------------------------------------------------------------------
    # TEST 7: Simulated Remediation Failure Resiliency in /api/v1/predict
    # ----------------------------------------------------------------------
    # Reset app anomaly state first
    client.post('/api/v1/predict', json={'cpu': 15.0, 'memory': 30.0, 'disk': 10.0, 'Service Status': 0, 'Health Check': 0})
    
    with patch('app.self_heal', side_effect=Exception('Process Terminate Permission Denied')):
        res7 = client.post('/api/v1/predict', json={
            'cpu': 98.0,
            'memory': 94.0,
            'disk': 89.0,
            'Service Status': 1,
            'Health Check': 1
        })
        d7 = res7.get_json()

    t7_pass = (
        res7.status_code == 200 and
        d7['is_anomaly'] is True and
        d7['prediction_label'] == 'Anomaly' and
        d7['healing_triggered'] is True and
        d7['healing_status'].startswith('failed') and
        'healing_error' in d7 and
        'Process Terminate Permission Denied' in d7['healing_error']
    )
    results['TEST 7'] = "PASS" if t7_pass else "FAIL"
    print(f"\nTEST 7 (Simulated Remediation Failure): {'PASS' if t7_pass else 'FAIL'}")
    print(f"  HTTP Status Code: {res7.status_code} (Never 500)")
    print(f"  Is Anomaly: {d7['is_anomaly']}")
    print(f"  Healing Status: {d7['healing_status']}")

    # Clean up test collector processes
    for proc in psutil.process_iter(['pid', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline') or []
            if any('collect_metrics.py' in arg for arg in cmdline):
                proc.terminate()
        except:
            pass

    # Spawn single clean collector process
    import subprocess
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    collector_script = os.path.join(backend_dir, 'monitoring', 'collect_metrics.py')
    subprocess.Popen([sys.executable, collector_script], start_new_session=True)

    print('\n======================================================================')
    all_pass = all([t1_pass, t2_pass, t3_pass, t4_pass, t5_pass, t6_pass, t7_pass])
    print(f"STEP 3 OVERALL STATUS: {'ALL 7 TESTS PASSED (100%)' if all_pass else 'FAILED'}")
    print('======================================================================')
    return all_pass

if __name__ == '__main__':
    success = run_step3_tests()
    sys.exit(0 if success else 1)
