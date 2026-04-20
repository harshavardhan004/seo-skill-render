from flask import Flask, render_template, request, send_file, redirect, url_for
import subprocess
import os
import uuid

# Using your custom 'Templates' folder name from our previous fix!
app = Flask(__name__, template_folder='Templates')


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    url = request.form.get("url")

    if not url:
        return "Error: URL is required", 400

    # 1. Create a unique ID for this specific report
    report_id = str(uuid.uuid4())
    report_filename = f"report_{report_id}.html"

    try:
        # 2. Run the script and save it with the unique filename
        subprocess.run([
            "python",
            "scripts/generate_report.py",
            url,
            "--output", report_filename
        ], check=True)

        # 3. Redirect the user to the brand-new page for this report
        return redirect(url_for("view_report", report_id=report_id))
    
    except subprocess.CalledProcessError:
        return "Error: The backend SEO script failed to run.", 500


# 4. Create a completely new route to display individual reports
@app.route("/report/<report_id>")
def view_report(report_id):
    report_filename = f"report_{report_id}.html"
    
    # Check if the file exists, then show it as a webpage
    if os.path.exists(report_filename):
        return send_file(report_filename)
    else:
        return "Error: Report not found or has expired.", 404


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
