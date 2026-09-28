"""
Dedicated Gemini AI Service Module
Provides Root Cause Analysis (RCA), intelligent remediation recommendations,
and AI Copilot chat assistance for cloud self-healing infrastructure.
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)

# Search for .env in Major_Project/ or workspace root
env_paths = [
    os.path.join(PROJECT_ROOT, ".env"),
    os.path.join(os.path.dirname(PROJECT_ROOT), ".env"),
    os.path.join(BACKEND_DIR, ".env")
]
for env_path in env_paths:
    if os.path.exists(env_path):
        load_dotenv(env_path)
        break

# Active Verified Gemini Model
GEMINI_MODEL = "gemini-3.6-flash"


def _get_client():
    """Retrieves an authenticated Gemini client using environment configuration."""
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in the environment or .env file.")
    return genai.Client(api_key=api_key)


def generate_rca(metrics: dict, is_anomaly: bool) -> dict:
    """
    Analyzes infrastructure telemetry metrics and generates a concise Root Cause Analysis (RCA).
    
    Args:
        metrics (dict): Dictionary of system telemetry (e.g. CPU, RAM, Disk, Latency).
        is_anomaly (bool): True if ML model classified the state as anomalous.
        
    Returns:
        dict: Structured result containing RCA diagnosis, anomaly status, and metadata.
    """
    try:
        client = _get_client()
        
        status_label = "CRITICAL ANOMALY DETECTED" if is_anomaly else "NOMINAL / HEALTHY STATE"
        
        prompt = (
            f"You are an expert Cloud Reliability Engineer and AI Diagnostic Engine.\n"
            f"System State: {status_label}\n"
            f"Live Telemetry Metrics:\n"
        )
        for key, val in metrics.items():
            prompt += f"- {key}: {val}\n"
            
        prompt += (
            f"\nInstructions:\n"
            f"Provide a concise Root Cause Analysis (2-3 sentences max). "
            f"Identify the specific resource bottleneck or state, explain the potential operational impact, "
            f"and assess the severity level (Low, Medium, High, or Critical)."
        )

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        
        rca_text = response.text.strip() if response and response.text else "Unable to generate analysis."
        
        return {
            "status": "success",
            "is_anomaly": is_anomaly,
            "rca": rca_text,
            "model": GEMINI_MODEL,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        return {
            "status": "error",
            "is_anomaly": is_anomaly,
            "error_type": type(e).__name__,
            "error_message": str(e),
            "rca": f"Automated fallback: Telemetry evaluated (Anomaly={is_anomaly}). Live AI diagnosis temporarily unavailable.",
            "model": GEMINI_MODEL,
            "timestamp": datetime.now().isoformat()
        }


def suggest_remediation(anomaly_context: dict or str) -> dict:
    """
    Generates intelligent step-by-step remediation suggestions for an active anomaly.
    
    Args:
        anomaly_context (dict or str): Telemetry metrics or anomaly description.
        
    Returns:
        dict: Recommended actions and automated recovery steps.
    """
    try:
        client = _get_client()
        
        prompt = (
            f"You are an Autonomous Cloud Self-Healing Engine.\n"
            f"Anomaly Context:\n{anomaly_context}\n\n"
            f"Instructions:\n"
            f"Provide a prioritized, bulleted list of 3-4 precise self-healing remediation actions "
            f"(e.g., auto-scale, memory garbage collection, pod restart, traffic rerouting) "
            f"to restore system stability with zero downtime."
        )

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        
        remediation_text = response.text.strip() if response and response.text else "No remediation plan generated."
        
        return {
            "status": "success",
            "remediation": remediation_text,
            "model": GEMINI_MODEL,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "remediation": "Fallback: Restart affected worker processes and flush ephemeral caches.",
            "model": GEMINI_MODEL,
            "timestamp": datetime.now().isoformat()
        }


def copilot_chat(user_question: str, telemetry_summary: dict or str = None) -> dict:
    """
    Interactive AI assistant for cluster observability and reliability inquiries.
    
    Args:
        user_question (str): User's operational question.
        telemetry_summary (dict or str, optional): Current cluster telemetry context.
        
    Returns:
        dict: AI Copilot response.
    """
    try:
        client = _get_client()
        
        prompt = (
            f"You are the AURA-HEAL AI Operations Copilot for a self-healing cloud platform.\n"
            f"Current Cluster Telemetry Context: {telemetry_summary or 'All nodes nominal.'}\n\n"
            f"User Question: {user_question}\n\n"
            f"Instructions: Provide a clear, concise, and helpful answer in 2-3 sentences."
        )

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        
        reply_text = response.text.strip() if response and response.text else "No response generated."
        
        return {
            "status": "success",
            "reply": reply_text,
            "model": GEMINI_MODEL,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "reply": "I am currently unable to query live AI recommendations. Cluster telemetry remains monitored.",
            "model": GEMINI_MODEL,
            "timestamp": datetime.now().isoformat()
        }


if __name__ == "__main__":
    # Self-test using sample telemetry metrics
    sample_metrics = {
        "CPU Usage (%)": 94.2,
        "Memory Usage (%)": 89.1,
        "Disk Usage (%)": 62.0,
        "Running Processes": 312,
        "Response Time (ms)": 145.0,
        "Service Status": "Degraded",
        "Health Check": "Unhealthy"
    }
    
    print("Testing generate_rca() with sample anomaly telemetry...")
    result = generate_rca(sample_metrics, is_anomaly=True)
    print("\n--- RCA Output ---")
    print(f"Status: {result.get('status')}")
    print(f"Model: {result.get('model')}")
    print(f"RCA:\n{result.get('rca')}")
