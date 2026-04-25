from flask import Flask, jsonify
from flask_cors import CORS
from scanner_engine import build_dashboard

app = Flask(__name__)
CORS(app)

@app.get("/")
def home():
    return jsonify({
        "name": "FL Strike Scanner API",
        "status": "ok",
        "endpoint": "/api/dashboard"
    })

@app.get("/api/dashboard")
def dashboard():
    try:
        return jsonify(build_dashboard())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
