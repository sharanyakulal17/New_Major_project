import os
import sys
import json
import psutil
import hashlib
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from healing.self_heal import (
    self_heal,
    restart_monitoring_service,
    verify_monitoring_service_health,
    map_rca_to_remediation_action,
    ACTION_RESTART_COLLECTOR,
    ACTION_NO_ACTION,
    LOG_FILE
)
from app import app
import test_step2
import test_step3

def run_step4_tests():
    client = app.test_client()
    results = {}

    print("======================================================================")
    print("STEP 4 VALIDATION SUITE: REAL POST-REMEDIATION HEALTH VERIFICATION")
    print("======================================================================\n")

    # ----------------------------------------------------------------------
    # TEST 1: Normal prediction -> no remediation, verification skipped
    # ----------------------------------------------------------------------
    with patch('healing.self_heal.restart_monitoring_service') as mock_restart_1:
        steps_1 = self_heal("Normal")
        t1_pass = (
            mock_restart_1.call_count == 0 and
            isinstance(steps_1, list) and
            hasattr(self_heal, 'last_healing_info') and
            self_heal.last_healing_info['verification'].get('status') == 'SKIPPED'
        )
    results['TEST 1'] = "PASS" if t1_pass else "FAIL"
    print(f"TEST 1 (Normal prediction -> verification skipped): {'PASS' if t1_pass else 'FAIL'}")

    # ----------------------------------------------------------------------
    # TEST 2: Anomaly with Full Successful Real Health Verification
    # ----------------------------------------------------------------------
    # Execute real remediation and full health verification against live collector
    success_2, msg_2, new_pid_2, old_pids_2, v_details_2 = restart_monitoring_service()
    
    t2_pass = (
        success_2 is True and
        new_pid_2 is not None and
        psutil.pid_exists(new_pid_2) and
        v_details_2.get('process_alive') is True and
        v_details_2.get('command_verified') is True and
        v_details_2.get('telemetry_readable') is True and
        v_details_2.get('latest_telemetry_available') is True and
        v_details_2.get('telemetry_fresh') is True and
        v_details_2.get('status') == 'SUCCESS'
    )
    results['TEST 2'] = "PASS" if t2_pass else "FAIL"
    print(f"\nTEST 2 (Anomaly with Full Successful Health Verification): {'PASS' if t2_pass else 'FAIL'}")
    print(f"  Spawned PID: {new_pid_2}")
    print(f"  Verification Details: {json.dumps(v_details_2, indent=2)}")

    # ----------------------------------------------------------------------
    # TEST 3: Simulate Stale Telemetry -> Freshness Check Fails
    # ----------------------------------------------------------------------
    stale_v_details = {
        "process_alive": True,
        "command_verified": True,
        "telemetry_readable": True,
        "latest_telemetry_available": True,
        "telemetry_fresh": False,
        "status": "FAILED",
        "reason": "Telemetry row is stale (95.0s old)"
    }
    with patch('healing.self_heal.verify_monitoring_service_health', return_value=(False, stale_v_details)):
        steps_3 = self_heal("Anomaly", rca="CPU Spike")
        t3_pass = (
            any("Verification Result: FAILED" in s for s in steps_3) and
            any("Recovery Failed" in s for s in steps_3) and
            self_heal.last_healing_info['success'] is False and
            self_heal.last_healing_info['verification']['telemetry_fresh'] is False
        )
    results['TEST 3'] = "PASS" if t3_pass else "FAIL"
    print(f"\nTEST 3 (Simulate Stale Telemetry -> Recovery Fails): {'PASS' if t3_pass else 'FAIL'}")

    # ----------------------------------------------------------------------
    # TEST 4: Simulate Missing/Corrupt Telemetry File -> Safe Failure
    # ----------------------------------------------------------------------
    corrupt_v_details = {
        "process_alive": True,
        "command_verified": True,
        "telemetry_readable": False,
        "latest_telemetry_available": False,
        "telemetry_fresh": False,
        "status": "FAILED",
        "reason": "Telemetry file unreadable or corrupt"
    }
    with patch('healing.self_heal.verify_monitoring_service_health', return_value=(False, corrupt_v_details)):
        steps_4 = self_heal("Anomaly", rca="Disk Failure")
        t4_pass = (
            any("Verification Result: FAILED" in s for s in steps_4) and
            any("Recovery Failed" in s for s in steps_4) and
            isinstance(steps_4, list)
        )
    results['TEST 4'] = "PASS" if t4_pass else "FAIL"
    print(f"\nTEST 4 (Simulate Missing/Corrupt Telemetry -> Safe Handling): {'PASS' if t4_pass else 'FAIL'}")

    # ----------------------------------------------------------------------
    # TEST 5: Simulate Process Failure (Dead PID) -> Health Check Fails
    # ----------------------------------------------------------------------
    proc_fail_details = {
        "process_alive": False,
        "command_verified": False,
        "telemetry_readable": False,
        "latest_telemetry_available": False,
        "telemetry_fresh": False,
        "status": "FAILED",
        "reason": "PID 99999 is not alive in process table"
    }
    with patch('healing.self_heal.verify_monitoring_service_health', return_value=(False, proc_fail_details)):
        steps_5 = self_heal("Anomaly", rca="Collector Deadlock")
        t5_pass = (
            any("Process Alive: FAIL" in s for s in steps_5) and
            any("Recovery Failed" in s for s in steps_5)
        )
    results['TEST 5'] = "PASS" if t5_pass else "FAIL"
    print(f"\nTEST 5 (Simulate Process Failure -> Reports Failure): {'PASS' if t5_pass else 'FAIL'}")

    # ----------------------------------------------------------------------
    # TEST 6: Gemini Failure Resiliency -> Health Verification Still Runs
    # ----------------------------------------------------------------------
    client.post('/api/v1/predict', json={'cpu': 15.0, 'memory': 30.0, 'disk': 10.0, 'Service Status': 0, 'Health Check': 0})
    with patch('app.generate_rca', side_effect=Exception('Simulated Gemini 503 Gateway Timeout')), \
         patch('healing.self_heal.restart_monitoring_service', return_value=(True, "OK", 8888, [], {"status": "SUCCESS", "telemetry_fresh": True})):
        res6 = client.post('/api/v1/predict', json={'cpu': 98.0, 'memory': 95.0, 'disk': 88.0, 'Service Status': 1, 'Health Check': 1})
        d6 = res6.get_json()
        t6_pass = (
            res6.status_code == 200 and
            d6['is_anomaly'] is True and
            d6['healing_triggered'] is True and
            d6['healing_status'] == 'executed' and
            d6['rca'] is None
        )
    results['TEST 6'] = "PASS" if t6_pass else "FAIL"
    print(f"\nTEST 6 (Gemini Failure Resiliency -> Health Verification Runs): {'PASS' if t6_pass else 'FAIL'}")

    # ----------------------------------------------------------------------
    # TEST 7: Run Existing Step 2 Regression Test
    # ----------------------------------------------------------------------
    print("\n--- Running Step 2 Regression Suite ---")
    t7_pass = test_step2.run_step2_tests()
    results['TEST 7 (Step 2 Regression)'] = "PASS" if t7_pass else "FAIL"

    # ----------------------------------------------------------------------
    # TEST 8: Run Existing Step 3 Regression Test
    # ----------------------------------------------------------------------
    print("\n--- Running Step 3 Regression Suite ---")
    t8_pass = test_step3.run_step3_tests()
    results['TEST 8 (Step 3 Regression)'] = "PASS" if t8_pass else "FAIL"

    # Clean up test collector processes
    for proc in psutil.process_iter(['pid', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline') or []
            if any('collect_metrics.py' in arg for arg in cmdline):
                proc.terminate()
        except:
            pass

    # Start single clean background collector
    import subprocess
    collector_script = os.path.join(BACKEND_DIR, 'monitoring', 'collect_metrics.py')
    subprocess.Popen([sys.executable, collector_script], start_new_session=True)

    print('\n======================================================================')
    all_pass = all([t1_pass, t2_pass, t3_pass, t4_pass, t5_pass, t6_pass, t7_pass, t8_pass])
    print(f"STEP 4 OVERALL STATUS: {'ALL 8 TESTS PASSED (100%)' if all_pass else 'FAILED'}")
    print('======================================================================')
    return all_pass

if __name__ == '__main__':
    success = run_step4_tests()
    sys.exit(0 if success else 1)
