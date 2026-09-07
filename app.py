"""Inbox dashboard API with Gmail OAuth and a demo fallback."""

import base64
import json
import os
import pathlib
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="Caspian Inbox Command")
app.mount("/static", StaticFiles(directory="static"), name="static")

DEMO_EMAILS: list[dict[str, Any]] = [
    {"id": "demo-1", "sender": "maya@northstar.io", "sender_name": "Maya Chen", "subject": "Final interview availability - Product Designer", "snippet": "Can we confirm Thursday at 2:00 PM for the final interview?", "time": "10:42 AM", "date": "Today", "priority": "urgent", "category": "Interview", "read": False, "labels": ["Interview", "Needs reply"], "body": "Hi, I can confirm Thursday at 2:00 PM for the final interview. Please share the panel details."},
    {"id": "demo-2", "sender": "hiring@orbitlabs.com", "sender_name": "Orbit Labs Hiring", "subject": "Shortlist review: 6 backend candidates", "snippet": "The shortlist is ready for your review before Friday.", "time": "9:18 AM", "date": "Today", "priority": "high", "category": "Shortlist", "read": False, "labels": ["Shortlist", "Due Friday"], "body": "The shortlist is ready for your review before Friday. Six candidates matched the backend role requirements."},
    {"id": "demo-3", "sender": "finance@vendor.co", "sender_name": "Vendor Finance", "subject": "Invoice 8491 is ready", "snippet": "Your monthly invoice is available in the billing portal.", "time": "Yesterday", "date": "Yesterday", "priority": "low", "category": "Finance", "read": True, "labels": ["Finance"], "body": "Your monthly invoice is available in the billing portal."},
]
TASKS: list[dict[str, Any]] = [
    {"id": "task-1", "title": "Confirm Maya Chen final interview", "source": "Final interview availability - Product Designer", "due": "Today", "priority": "urgent", "status": "open", "assignee": "You"},
    {"id": "task-2", "title": "Review backend candidate shortlist", "source": "Shortlist review: 6 backend candidates", "due": "Friday", "priority": "high", "status": "open", "assignee": "You"},
]


class TaskCreate(BaseModel):
    title: str
    due: str = "No deadline"
    priority: str = "medium"
    source: str = "Dashboard"


def gmail_service():
    secrets = os.environ.get("GOOGLE_CLIENT_SECRETS_FILE", "credentials.json")
    token_path = pathlib.Path("token.json")
    if not pathlib.Path(secrets).exists() or not token_path.exists():
        return None
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    credentials = Credentials.from_authorized_user_file(str(token_path), ["https://www.googleapis.com/auth/gmail.readonly"])
    return build("gmail", "v1", credentials=credentials)


def live_emails() -> list[dict[str, Any]]:
    service = gmail_service()
    if not service:
        return DEMO_EMAILS
    from googleapiclient.errors import HttpError

    try:
        response = service.users().messages().list(userId="me", q="newer_than:14d", maxResults=10).execute()
    except HttpError:
        return DEMO_EMAILS
    messages = []
    for item in response.get("messages", []):
        try:
            raw = service.users().messages().get(userId="me", id=item["id"], format="full").execute()
        except HttpError:
            continue
        headers = {h["name"].lower(): h["value"] for h in raw.get("payload", {}).get("headers", [])}
        body = raw.get("snippet", "")
        sender = headers.get("from", "Unknown sender")
        sender_name = re.sub(r"\s*<.*>", "", sender).strip().strip('"') or sender
        lower = f"{headers.get('subject', '')} {body}".lower()
        priority = "urgent" if any(word in lower for word in ("urgent", "asap", "interview", "deadline")) else "high" if any(word in lower for word in ("shortlist", "review", "action")) else "low"
        messages.append({"id": item["id"], "sender": sender, "sender_name": sender_name, "subject": headers.get("subject", "No subject"), "snippet": body, "time": headers.get("date", ""), "date": "Recent", "priority": priority, "category": "Interview" if "interview" in lower else "Shortlist" if "shortlist" in lower else "General", "read": "UNREAD" not in raw.get("labelIds", []), "labels": [], "body": body})
    return messages


@app.get("/")
def index():
    return FileResponse("static/index.html")


@app.get("/api/overview")
def overview():
    emails = live_emails()
    return {"emails": emails, "tasks": TASKS, "connected": gmail_service() is not None, "account": os.environ.get("GMAIL_ACCOUNT", "Connect a Gmail account"), "updated": datetime.now(timezone.utc).isoformat()}


@app.post("/api/tasks")
def create_task(task: TaskCreate):
    item = {"id": f"task-{uuid.uuid4().hex[:8]}", **task.model_dump(), "status": "open", "assignee": "You"}
    TASKS.insert(0, item)
    return item


@app.patch("/api/tasks/{task_id}")
def update_task(task_id: str):
    for task in TASKS:
        if task["id"] == task_id:
            task["status"] = "done" if task["status"] == "open" else "open"
            return task
    raise HTTPException(status_code=404, detail="Task not found")


@app.get("/auth/gmail")
def auth_gmail():
    from google_auth_oauthlib.flow import Flow
    secrets = os.environ.get("GOOGLE_CLIENT_SECRETS_FILE", "credentials.json")
    if not pathlib.Path(secrets).exists():
        return RedirectResponse("/?error=Add+credentials.json+from+Google+Cloud+Console+first")
    flow = Flow.from_client_secrets_file(secrets, scopes=["https://www.googleapis.com/auth/gmail.readonly"], redirect_uri="http://localhost:8000/auth/gmail/callback")
    authorization_url, state = flow.authorization_url(access_type="offline", prompt="consent")
    pathlib.Path(".oauth-state").write_text(json.dumps({"state": state, "code_verifier": flow.code_verifier}), encoding="utf-8")
    return RedirectResponse(authorization_url)


@app.get("/auth/gmail/callback")
def auth_callback(code: str, state: str):
    from google_auth_oauthlib.flow import Flow
    secrets = os.environ.get("GOOGLE_CLIENT_SECRETS_FILE", "credentials.json")
    flow = Flow.from_client_secrets_file(secrets, scopes=["https://www.googleapis.com/auth/gmail.readonly"], state=state, redirect_uri="http://localhost:8000/auth/gmail/callback")
    oauth_state = json.loads(pathlib.Path(".oauth-state").read_text(encoding="utf-8"))
    if state != oauth_state["state"]:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    flow.code_verifier = oauth_state["code_verifier"]
    flow.fetch_token(code=code)
    pathlib.Path("token.json").write_text(flow.credentials.to_json(), encoding="utf-8")
    return RedirectResponse("/")


@app.get("/api/emails/{email_id}")
def email_detail(email_id: str):
    email = next((item for item in live_emails() if item["id"] == email_id), None)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    return email
