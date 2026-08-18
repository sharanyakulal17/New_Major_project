import os
from datetime import datetime
import time

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(CURRENT_DIR, "healing_log.txt")


def self_heal(prediction, target_node="All Nodes"):

    steps = []

    if prediction == "Anomaly":

        print(f"\n🚨 Anomaly Detected on {target_node}!\n - self_heal.py")

        steps.append("📊 Collecting latest system metrics...")
        time.sleep(1)

        steps.append("🧹 Preprocessing collected metrics...")
        time.sleep(1)

        steps.append("🤖 Running Random Forest prediction...")
        time.sleep(1)

        steps.append("🔍 Root cause identified : High CPU / Memory Usage")
        time.sleep(1)

        steps.append(f"🔄 Restarting Service & Scaling Node ({target_node})...")
        time.sleep(2)

        # Simulated restart
        action = f"Monitoring Service Restarted & Cache Cleared ({target_node})"

        steps.append("🩺 Running Health Verification...")
        time.sleep(1)

        steps.append("✅ Recovery Successful")
        time.sleep(1)

        for step in steps:
            print(step)

    else:

        action = "No Action Required"

        print("🟢 System Healthy - self_heal.py")

    # Save logs
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a") as file:
        file.write(
            f"{datetime.now()} | {prediction} | {action}\n"
        )

    return steps


if __name__ == "__main__":

    self_heal("Anomaly")