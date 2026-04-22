from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# ----------------------------
# CONFIG (replace with yours)
# ----------------------------
GITHUB_TOKEN = "your_github_token"

#JIRA_URL = "https://your-domain.atlassian.net"
#JIRA_EMAIL = "your-email"
#JIRA_API_TOKEN = "your-jira-token"
#JIRA_PROJECT = "SEC"

#JIRA_AUTH = (JIRA_EMAIL, JIRA_API_TOKEN)


# ----------------------------
# CLASSIFIER
# ----------------------------
def classify_event(event):
    score = 0

    if event.get("override"):
        score += 50
    if event.get("failed_checks", 0) > 3:
        score += 30
    if event.get("author_role") == "external":
        score += 20

    if score >= 70:
        return "HIGH"
    elif score >= 40:
        return "MEDIUM"
    return "LOW"


# ----------------------------
# GITHUB FETCH
# ----------------------------
def get_pr_details(pr_url):
    if not pr_url:
        return {}

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}"
    }

    res = requests.get(pr_url, headers=headers)

    if res.status_code != 200:
        return {}

    pr = res.json()

    return {
        "title": pr.get("title"),
        "author": pr.get("user", {}).get("login"),
        "changed_files": pr.get("changed_files"),
        "additions": pr.get("additions"),
        "deletions": pr.get("deletions"),
    }


# ----------------------------
# JIRA INTEGRATION
# ----------------------------
#def create_or_update_ticket(event, severity, pr_data):
    summary = f"[{severity}] Override - {pr_data.get('title', 'No PR Title')}"

    search_url = f"{JIRA_URL}/rest/api/3/search"
    jql = f'summary ~ "{summary}"'

    search_res = requests.get(
        search_url,
        headers={"Accept": "application/json"},
        auth=JIRA_AUTH,
        params={"jql": jql}
    ).json()

    if search_res.get("issues"):
        return search_res["issues"][0]["key"]

    create_url = f"{JIRA_URL}/rest/api/3/issue"

    payload = {
        "fields": {
            "project": {"key": JIRA_PROJECT},
            "summary": summary,
            "description": str(event),
            "issuetype": {"name": "Task"}
        }
    }

    res = requests.post(
        create_url,
        json=payload,
        headers={"Content-Type": "application/json"},
        auth=JIRA_AUTH
    ).json()

    return res.get("key")


# ----------------------------
# ROUTING LOGIC
# ----------------------------
def route_issue(severity):
    if severity == "HIGH":
        return "AppSec Team"
    elif severity == "MEDIUM":
        return "Senior Developer"
    return "Developer"


# ----------------------------
# TEST ROUTE (browser check)
# ----------------------------
@app.route("/", methods=["GET"])
def home():
    return "Webhook Service is Running 🚀"


# ----------------------------
# MAIN WEBHOOK
# ----------------------------
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    severity = classify_event(data)
    pr_data = get_pr_details(data.get("pull_request_url"))

    ticket = create_or_update_ticket(data, severity, pr_data)
    assignee = route_issue(severity)

    return jsonify({
        "severity": severity,
        "ticket": ticket,
        "assigned_to": assignee,
        "pr_data": pr_data
    })


# ----------------------------
# RUN SERVER
# ----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)