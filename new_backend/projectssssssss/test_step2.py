import os
import sys
import json
import psutil
from unittest.mock import patch, MagicMock

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import app, is_active_anomaly, HEAL_LOG_FILE

def run_step2_tests():
    client = app.test_client()
    results = {}

    print("======================================================================")
    print("STEP 2 VALIDATION SUITE: 7 SCENARIOS")
    print("======================================================================\n")

    # ----------------------------------------------------------------------
    # TEST 1: Normal telemetry
    # ----------------------------------------------------------------------
    with patch('app.generate_rca') as mock_gemini_1, patch('app.self_heal') as mock_heal_1:
        res1 = client.post('/api/v1/predict', json={
            'cpu': 20.0,
            'memory': 40.0,
            'disk': 15.0,
            'Service Status': 0,
            'Health Check': 0
        })
        d1 = res1.get_json()
        t1_pass = (
            res1.status_code == 200 and
            d1['is_anomaly'] is False and
            d1['prediction_label'] == 'Normal' and
            d1['healing_triggered'] is False and
            d1['healing_status'] == 'nominal' and
            d1['rca'] is None and
            mock_gemini_1.call_count == 0 and
            mock_heal_1.call_count == 0
        )
        results['TEST 1'] = "PASS" if t1_pass else "FAIL"
        print(f"TEST 1 (Normal telemetry): {'PASS' if t1_pass else 'FAIL'}")
        print("  Response:", json.dumps(d1, indent=2))

    # ----------------------------------------------------------------------
    # TEST 2: First anomaly
    # ----------------------------------------------------------------------
    mock_rca_text = "Root Cause Analysis: Extreme CPU (98.5%) and Memory (95.0%) contention."
    with patch('app.generate_rca', return_value={'status': 'success', 'rca': mock_rca_text}) as mock_gemini_2, \
         patch('app.self_heal', return_value=['Step 1', 'Step 2']) as mock_heal_2:
        
        res2 = client.post('/api/v1/predict', json={
            'cpu': 98.5,
            'memory': 95.0,
            'disk': 88.0,
            'Service Status': 1,
            'Health Check': 1
        })
        d2 = res2.get_json()

        t2_pass = (
            res2.status_code == 200 and
            d2['is_anomaly'] is True and
            d2['prediction_label'] == 'Anomaly' and
            d2['healing_triggered'] is True and
            d2['healing_status'] == 'executed' and
            d2['rca'] == mock_rca_text and
            mock_gemini_2.call_count == 1 and
            mock_heal_2.call_count == 1
        )
        results['TEST 2'] = "PASS" if t2_pass else "FAIL"
        print(f"\nTEST 2 (First anomaly): {'PASS' if t2_pass else 'FAIL'}")
        print("  Response:", json.dumps(d2, indent=2))

    # ----------------------------------------------------------------------
    # TEST 3: Repeated anomaly immediately after TEST 2
    # ----------------------------------------------------------------------
    with patch('app.generate_rca') as mock_gemini_3, patch('app.self_heal') as mock_heal_3:
        res3 = client.post('/api/v1/predict', json={
            'cpu': 99.0,
            'memory': 96.0,
            'disk': 90.0,
            'Service Status': 1,
            'Health Check': 1
        })
        d3 = res3.get_json()

        t3_pass = (
            res3.status_code == 200 and
            d3['is_anomaly'] is True and
            d3['prediction_label'] == 'Anomaly' and
            d3['healing_triggered'] is False and
            d3['healing_status'] == 'active_remediation_in_progress' and
            d3['rca'] == mock_rca_text and
            mock_gemini_3.call_count == 0 and
            mock_heal_3.call_count == 0
        )
        results['TEST 3'] = "PASS" if t3_pass else "FAIL"
        print(f"\nTEST 3 (Repeated anomaly): {'PASS' if t3_pass else 'FAIL'}")
        print("  Response:", json.dumps(d3, indent=2))

    # ----------------------------------------------------------------------
    # TEST 4: Normal telemetry after anomaly (Recovery)
    # ----------------------------------------------------------------------
    with patch('app.generate_rca') as mock_gemini_4, patch('app.self_heal') as mock_heal_4:
        res4 = client.post('/api/v1/predict', json={
            'cpu': 22.0,
            'memory': 35.0,
            'disk': 15.0,
            'Service Status': 0,
            'Health Check': 0
        })
        d4 = res4.get_json()
        t4_pass = (
            res4.status_code == 200 and
            d4['is_anomaly'] is False and
            d4['prediction_label'] == 'Normal' and
            d4['healing_triggered'] is False and
            d4['healing_status'] == 'nominal' and
            d4['rca'] is None and
            mock_gemini_4.call_count == 0 and
            mock_heal_4.call_count == 0
        )
        results['TEST 4'] = "PASS" if t4_pass else "FAIL"
        print(f"\nTEST 4 (Normal telemetry recovery): {'PASS' if t4_pass else 'FAIL'}")
        print("  Response:", json.dumps(d4, indent=2))

    # ----------------------------------------------------------------------
    # TEST 5: New anomaly after recovery
    # ----------------------------------------------------------------------
    mock_rca_2 = "Root Cause Analysis: Memory Saturation (92.0%)."
    with patch('app.generate_rca', return_value={'status': 'success', 'rca': mock_rca_2}) as mock_gemini_5, \
         patch('app.self_heal', return_value=['Step 1', 'Step 2']) as mock_heal_5:
        
        res5 = client.post('/api/v1/predict', json={
            'cpu': 97.0,
            'memory': 92.0,
            'disk': 85.0,
            'Service Status': 1,
            'Health Check': 1
        })
        d5 = res5.get_json()

        t5_pass = (
            res5.status_code == 200 and
            d5['is_anomaly'] is True and
            d5['prediction_label'] == 'Anomaly' and
            d5['healing_triggered'] is True and
            d5['healing_status'] == 'executed' and
            d5['rca'] == mock_rca_2 and
            mock_gemini_5.call_count == 1 and
            mock_heal_5.call_count == 1
        )
        results['TEST 5'] = "PASS" if t5_pass else "FAIL"
        print(f"\nTEST 5 (New anomaly after recovery): {'PASS' if t5_pass else 'FAIL'}")
        print("  Response:", json.dumps(d5, indent=2))

    # Reset to normal before failover tests
    client.post('/api/v1/predict', json={
        'cpu': 20.0,
        'memory': 30.0,
        'disk': 10.0,
        'Service Status': 0,
        'Health Check': 0
    })

    # ----------------------------------------------------------------------
    # TEST 6: Simulate Gemini failure
    # ----------------------------------------------------------------------
    with patch('app.generate_rca', side_effect=Exception('Simulated Gemini 503 Gateway Timeout')) as mock_gemini_6, \
         patch('app.self_heal', return_value=['Fallback Step 1']) as mock_heal_6:
        
        res6 = client.post('/api/v1/predict', json={
            'cpu': 98.0,
            'memory': 94.0,
            'disk': 89.0,
            'Service Status': 1,
            'Health Check': 1
        })
        d6 = res6.get_json()

        t6_pass = (
            res6.status_code == 200 and
            d6['is_anomaly'] is True and
            d6['prediction_label'] == 'Anomaly' and
            d6['healing_triggered'] is True and
            d6['healing_status'] == 'executed' and
            d6['rca'] is None and
            mock_gemini_6.call_count == 1 and
            mock_heal_6.call_count == 1
        )
        results['TEST 6'] = "PASS" if t6_pass else "FAIL"
        print(f"\nTEST 6 (Simulate Gemini failure): {'PASS' if t6_pass else 'FAIL'}")
        print("  Response:", json.dumps(d6, indent=2))

    # Reset to normal before self-heal failure test
    client.post('/api/v1/predict', json={
        'cpu': 20.0,
        'memory': 30.0,
        'disk': 10.0,
        'Service Status': 0,
        'Health Check': 0
    })

    # ----------------------------------------------------------------------
    # TEST 7: Simulate self_heal() failure
    # ----------------------------------------------------------------------
    with patch('app.generate_rca', return_value={'status': 'success', 'rca': 'RCA Details'}), \
         patch('app.self_heal', side_effect=Exception('Process Terminate Permission Denied')):
        
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
            'failed' in d7['healing_status'] and
            'healing_error' in d7 and
            'Process Terminate Permission Denied' in d7['healing_error']
        )
        results['TEST 7'] = "PASS" if t7_pass else "FAIL"
        print(f"\nTEST 7 (Simulate self_heal failure): {'PASS' if t7_pass else 'FAIL'}")
        print("  Response:", json.dumps(d7, indent=2))

    print('\n======================================================================')
    all_pass = all([t1_pass, t2_pass, t3_pass, t4_pass, t5_pass, t6_pass, t7_pass])
    print(f"STEP 2 OVERALL STATUS: {'ALL 7 TESTS PASSED (100%)' if all_pass else 'FAILED'}")
    print('======================================================================')
    return all_pass

if __name__ == '__main__':
    success = run_step2_tests()
    sys.exit(0 if success else 1)
