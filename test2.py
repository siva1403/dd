from flask import Flask, request, jsonify
import requests
import os
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# ---- Email Config ----
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_USER = os.getenv("EMAIL_USER")       # your emailhhhhhhh
EMAIL_PASS = os.getenv("EMAIL_PASS")       # app password
EMAIL_TO = "recipient@eple.com"


def send_email(subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_TO

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)


def get_commit_status(repo, sha):
    url = f"https://api.github.com/repos/{repo}/commits/{sha}/status"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    return r.json()


@app.route("/webhook", methods=["POST"])
def webhook():
    event = request.headers.get("X-GitHub-Event")
    payload = request.json

    # ---- Pull Request merged ----
    if event == "pull_request":
        action = payload.get("action")
        pr = payload.get("pull_request")

        if action == "closed" and pr.get("merged"):
            repo = payload["repository"]["full_name"]
            sha = pr["merge_commit_sha"]

            status = get_commit_status(repo, sha)

            if status.get("state") != "success":
                subject = "⚠️ Branch Protection Override Detected"

                body = f"""
Repository: {repo}
PR URL: {pr['html_url']}
Merged by: {pr['merged_by']['login']}
Commit SHA: {sha}
Status: {status.get('state')}

⚠️ This PR may have been merged by bypassing required checks.
"""

                send_email(subject, body)

    # ---- Force push detection ----
    elif event == "push":
        if payload.get("forced"):
            repo = payload["repository"]["full_name"]
            ref = payload.get("ref")
            sender = payload["sender"]["login"]

            subject = "⚠️ Force Push Detected on Protected Branch"

            body = f"""
Repository: {repo}
Branch: {ref}
User: {sender}

⚠️ A force push was made, which may indicate a protection rule override.
"""

            send_email(subject, body)

    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(port=5000)
