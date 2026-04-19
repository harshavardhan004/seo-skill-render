from flask import Flask, request, jsonify
import subprocess
import os
import uuid

app = Flask(__name__)

@app.route("/")
def home():
    return {"status": "SEO API Running"}

@app.route("/seo-audit", methods=["POST"])
def seo_audit():

    data = request.json
    url = data.get("url")
    email = data.get("email")

    if not url:
        return jsonify({"error": "URL required"}), 400

    report_id = str(uuid.uuid4())
    output_file = f"reports/report_{report_id}.html"

    os.makedirs("reports", exist_ok=True)

    subprocess.run([
        "python",
        "scripts/generate_report.py",
        url
    ])

    return jsonify({
        "status": "Processing Started",
        "report_id": report_id,
        "url": url
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)