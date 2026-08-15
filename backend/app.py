from flask import Flask
from dashboard.dashboard import dashboard

app = Flask(__name__)

app.register_blueprint(dashboard)

if __name__ == "__main__":
    app.run(debug=True)