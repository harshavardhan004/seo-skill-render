from flask import Flask, render_template, request, send_file
import subprocess
import os

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():

    email = request.form.get("email")
    url = request.form.get("url")

    subprocess.run([
        "python",
        "scripts/generate_report.py",
        url
    ])

    return send_file("report.html")


if __name__ == "__main__":
    # Dynamically bind to Render's assigned port
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)