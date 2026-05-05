import requests
import time
from datetime import datetime
from zoneinfo import ZoneInfo
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
GITHUB_TOKEN = os.environ["HUB_TOKEN"]
EMAIL_USER = os.environ["EMAIL_USER"]
EMAIL_PASS = os.environ["EMAIL_PASS"]
EMAIL_TO = os.environ["EMAIL_TO"]
CHECK_INTERVAL = 120
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}
REQUIRED_CHECKS = [
    "WhiteSource Security Check",
    "Qwiet Vulnerability Check",
    "Nightfall DLP",
    "SharecareAppSec",
    "WhiteSource Code Security Check"
]
alerted_prs = set()
def send_email(subject, body):
    try:
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = EMAIL_USER
        msg["To"] = EMAIL_TO
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        print("📧 Email sent")
    except Exception as e:
        print("❌ Email error:", e)
def get_repos():
    url = "https://api.github.com/user/repos?per_page=100&type=owner"
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        print("❌ Repo error:", res.text)
        return []
    return [
        r for r in res.json()
        if not r.get("archived") and not r.get("fork")
    ]
def get_open_prs(repo):
    url = f"https://api.github.com/repos/{repo}/pulls?state=open"
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        return []
    return res.json()
def get_check_runs(repo, sha):
    url = f"https://api.github.com/repos/{repo}/commits/{sha}/check-runs"
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        return []
    return res.json().get("check_runs", [])
def get_commit_email(repo, sha):
    url = f"https://api.github.com/repos/{repo}/commits/{sha}"
    res = requests.get(url, headers=HEADERS)

    if res.status_code != 200:
        return None
    return res.json().get("commit", {}).get("author", {}).get("email")
def analyze_checks(checks):
    issues = []
    for req in REQUIRED_CHECKS:
        matched = [c for c in checks if req.lower() in c["name"].lower()]
        if not matched:
            issues.append(f"{req} - Not found")
        else:
            for m in matched:
                if m["conclusion"] == "failure":
                    issues.append(f"{m['name']} - failure")
    return issues
def monitor():
    print("🚀 Personal GitHub PR monitoring started...\n")
    start_time = datetime.now(ZoneInfo("Asia/Kolkata"))
    while True:
        try:
            repos = get_repos()
            for repo in repos:
                repo_name = repo["full_name"]
                prs = get_open_prs(repo_name)
                for pr in prs:
                    pr_id = pr["id"]
                    sha = pr["head"]["sha"]
                    user = pr["user"]["login"]
                    alert_key = f"{pr_id}-{sha}"
                    if alert_key in alerted_prs:
                        continue
                    pr_time = datetime.fromisoformat(
                        pr["created_at"].replace("Z", "+00:00")
                    ).astimezone(ZoneInfo("Asia/Kolkata"))
                    if pr_time < start_time:
                        continue
                    checks = get_check_runs(repo_name, sha)
                    issues = analyze_checks(checks)
                    if issues:
                        commit_email = get_commit_email(repo_name, sha)
                        if not commit_email:
                            commit_email = f"{user}@users.noreply.github.com"
                        commit_id = sha[:7]
                        commit_url = f"https://github.com/{repo_name}/commit/{sha}"

                        formatted_time = pr_time.strftime("%d-%m-%Y %H:%M:%S IST")

                        message = f"""
repo_name: {repo_name}
PR_URL: {pr['html_url']}
commit_id: {commit_id}
commit_sha: {sha}
commit_url: {commit_url}
user: {user}
user_email: {commit_email}
committed_time: {formatted_time}

issues:
{chr(10).join(issues)}
-----------------------------------------
"""

                        send_email("🚨 PR Security Alert", message)
                        alerted_prs.add(alert_key)

        except Exception as e:
            print("❌ Global error:", e)

        print(f"⏳ Waiting {CHECK_INTERVAL} seconds...\n")
        time.sleep(CHECK_INTERVAL)


# -------------------------------
# RUN
# -------------------------------
if __name__ == "__main__":
    monitor()
