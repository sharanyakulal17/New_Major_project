import os
import sys
from flask import Flask
from dashboard.dashboard import dashboard

app = Flask(__name__, static_folder=None)

# Register dashboard blueprint serving the React frontend and APIs
app.register_blueprint(dashboard)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print("\n=======================================================")
    print(f"🚀 Major_Project Flask Self-Healing Server Running")
    print(f"🌐 Dashboard UI & API: http://127.0.0.1:{port}")
    print("=======================================================\n")
    app.run(host="0.0.0.0", port=port, debug=True)