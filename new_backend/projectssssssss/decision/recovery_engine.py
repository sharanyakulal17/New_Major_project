# decision/recovery_engine.py

import math


# Possible recovery actions
NO_ACTION = "NO_ACTION"
RESTART = "RESTART"
SCALE_OUT = "SCALE_OUT"
SCALE_IN = "SCALE_IN"
REROUTE = "REROUTE"
REPLACE_INSTANCE = "REPLACE_INSTANCE"
ESCALATE = "ESCALATE"


def get_number(metrics, key, default=0.0):
    """
    Safely get a numeric value from the metrics dictionary.
    """
    try:
        return float(metrics.get(key, default))
    except (TypeError, ValueError):
        return default


def predict_workload(metrics):
    """
    Estimate the current workload level.

    This is a lightweight decision score used by the
    recovery engine. It is not the ML model prediction.
    """

    cpu = get_number(metrics, "cpu")
    memory = get_number(metrics, "memory")
    disk = get_number(metrics, "disk")
    latency = get_number(metrics, "latency")
    error_rate = get_number(metrics, "error_rate")

    # Convert latency and error rate into a 0-100 scale
    latency_score = min(latency / 5, 100)
    error_score = min(error_rate * 5, 100)

    workload_score = max(
    cpu,
    memory,
    disk,
    latency_score,
    error_score
    )

    if workload_score >= 80:
        level = "HIGH"
    elif workload_score >= 55:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        "level": level,
        "score": round(workload_score, 2)
    }


def choose_recovery_action(
    metrics,
    rca="",
    current_instances=1,
    min_instances=1,
    max_instances=20,
    anomaly=False
):
    """
    Decide what AURA-HEAL should do after detecting an anomaly.

    Possible decisions:
        NO_ACTION
        RESTART
        SCALE_OUT
        SCALE_IN
        REROUTE
        REPLACE_INSTANCE
        ESCALATE
    """

    cpu = get_number(metrics, "cpu")
    memory = get_number(metrics, "memory")
    latency = get_number(metrics, "latency")
    error_rate = get_number(metrics, "error_rate")

    rca_text = str(rca).lower()

    workload = predict_workload(metrics)

    # Keywords that help us understand the RCA
    traffic_problem = any(
        word in rca_text
        for word in [
            "traffic",
            "overload",
            "high cpu",
            "cpu spike",
            "capacity",
            "load"
        ]
    )

    memory_problem = any(
        word in rca_text
        for word in [
            "memory",
            "memory leak",
            "out of memory",
            "oom"
        ]
    )

    disk_problem = any(word in rca_text for word in ["disk","storage","disk full","storage full"])

    network_problem = any(
        word in rca_text
        for word in [
            "network",
            "latency",
            "connection",
            "timeout"
        ]
    )

    crash_problem = any(
        word in rca_text
        for word in [
            "crash",
            "failed",
            "failure",
            "service down",
            "unavailable"
        ]
    )

    # --------------------------------------------------
    # Decision 1: Critical crash / service failure
    # --------------------------------------------------

    if crash_problem:
        action = REPLACE_INSTANCE

        reason = (
            "A service or instance failure was detected. "
            "Replacing the unhealthy instance provides a "
            "fresh application instance."
        )

    # --------------------------------------------------
    # Decision 2: Network / latency problem
    # --------------------------------------------------

    elif (network_problem or latency >= 300) and not traffic_problem:

        if anomaly and current_instances < max_instances:
            action = SCALE_OUT

            reason = (
                "High latency was detected during an active anomaly. "
                "Additional capacity is recommended to distribute the workload."
            )
        else:
            action = REROUTE

            reason = (
                "Network or latency problems were detected. "
                "Traffic should be redirected to a healthier route."
            )

    # --------------------------------------------------
    # Decision 3: Heavy traffic / CPU overload
    # --------------------------------------------------

    elif traffic_problem or cpu >= 88:

        if current_instances < max_instances:
            action = SCALE_OUT

            reason = (
                "The workload is high and CPU utilization is elevated. "
                "Adding another instance can distribute the workload."
            )
        else:
            action = ESCALATE

            reason = (
                "Workload is high but the maximum instance limit "
                "has already been reached."
            )

    # --------------------------------------------------
    # Decision 4: Memory problem
    # --------------------------------------------------

    elif memory_problem or memory >= 90:

        action = RESTART

        reason = (
            "Memory utilization is critically high. "
            "Restarting the affected service can release "
            "unnecessary memory usage."
        )

    elif disk_problem or disk >= 90:

        action = RESTART

        reason = (
            "Disk utilization is critically high. "
            "Restarting the affected service can help "
            "recover disk resources and restore normal operation."
        )
    # --------------------------------------------------
    # Decision 5: Anomaly but no known cause
    # --------------------------------------------------

    elif anomaly:

        action = ESCALATE

        reason = (
            "An anomaly was detected, but the recovery engine "
            "could not confidently identify a safe automated action."
        )

    # --------------------------------------------------
    # Decision 6: System is healthy
    # --------------------------------------------------

    else:

        action = NO_ACTION

        reason = (
            "The monitored metrics are within acceptable limits. "
            "No recovery action is required."
        )

    return {
        "action": action,
        "reason": reason,
        "workload_level": workload["level"],
        "workload_score": workload["score"],
        "metrics": {
            "cpu": cpu,
            "memory": memory,
            "disk": disk,
            "latency": latency,
            "error_rate": error_rate
        },
        "current_instances": current_instances,
        "recommended_instances": (
            current_instances + 1
            if action == SCALE_OUT
            else current_instances
        )
    }


def simulate_what_if(
    metrics,
    traffic_increase_percent,
    current_instances=1
):
    """
    Simulate what could happen if traffic increases.

    This is a demonstration / planning simulation.
    It does not create real cloud instances.
    """

    cpu = get_number(metrics, "cpu")
    memory = get_number(metrics, "memory")
    latency = get_number(metrics, "latency")

    current_instances = max(1, int(current_instances))

    increase = max(0, float(traffic_increase_percent)) / 100

    # Projected values
    projected_cpu = min(
        100,
        cpu * (1 + increase)
    )

    projected_memory = min(
        100,
        memory * (1 + increase * 0.5)
    )

    projected_latency = (
        latency * (1 + increase * 0.8)
    )

    # We try to keep CPU around 70%
    required_instances = max(
        current_instances,
        math.ceil(projected_cpu / 70)
    )

    if required_instances > current_instances:

        recommended_action = SCALE_OUT

    else:

        recommended_action = NO_ACTION

    # Estimate values after distributing workload
    after_cpu = projected_cpu * (
        current_instances / required_instances
    )

    after_memory = projected_memory * (
        current_instances / required_instances
    )

    after_latency = projected_latency * (
        current_instances / required_instances
    )

    instances_to_add = (
        required_instances - current_instances
    )

    return {
        "traffic_increase_percent": traffic_increase_percent,

        "current_instances": current_instances,

        "predicted": {
            "cpu": round(projected_cpu, 2),
            "memory": round(projected_memory, 2),
            "latency": round(projected_latency, 2)
        },

        "recommended_instances": required_instances,

        "instances_to_add": instances_to_add,

        "recommended_action": recommended_action,

        "estimated_after_scaling": {
            "cpu": round(after_cpu, 2),
            "memory": round(after_memory, 2),
            "latency": round(after_latency, 2)
        }
    }