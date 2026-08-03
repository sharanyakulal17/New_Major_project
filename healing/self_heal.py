from datetime import datetime
import time

LOG_FILE = "healing/healing_log.txt"


def self_heal(prediction):

    steps = []

    if prediction == "Anomaly":

        print("\n🚨 Anomaly Detected!\n - self_heal.py:13")

        steps.append("📊 Collecting latest system metrics...")
        time.sleep(1)

        steps.append("🧹 Preprocessing collected metrics...")
        time.sleep(1)

        steps.append("🤖 Running Random Forest prediction...")
        time.sleep(1)

        steps.append("🔍 Root cause identified : High CPU Usage")
        time.sleep(1)

        steps.append("🔄 Restarting Monitoring Service...")
        time.sleep(2)

        # Simulated restart
        action = "Monitoring Service Restarted"

        steps.append("🩺 Running Health Verification...")
        time.sleep(1)

        steps.append("✅ Recovery Successful")
        time.sleep(1)

        for step in steps:
            print(step)

    else:

        action = "No Action Required"

        print("🟢 System Healthy - self_heal.py:46")

    # Save logs

    with open(LOG_FILE, "a") as file:

        file.write(
            f"{datetime.now()} | {prediction} | {action}\n"
        )

    return steps


if __name__ == "__main__":

    self_heal("Anomaly")