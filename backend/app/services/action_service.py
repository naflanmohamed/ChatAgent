import base64
from email.mime.text import MIMEText
from email.utils import parseaddr
from datetime import datetime, timezone

from googleapiclient.discovery import build

from app.core.config import settings
from app.integrations.google_client import get_valid_credentials, save_refreshed_token
from app.db.models import Approval


def _google_services(db, user):
    creds = get_valid_credentials(user)
    save_refreshed_token(db, user, creds)
    return build("gmail", "v1", credentials=creds), build("calendar", "v3", credentials=creds)


def execute_approved_action(db, user, approval: Approval):
    payload = approval.payload or {}
    gmail_service, calendar_service = _google_services(db, user)

    if approval.action_type == "send_email":
        message = MIMEText(payload["body"])
        message["to"] = payload["to"]
        message["subject"] = payload["subject"]
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        result = gmail_service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return {"status": "sent", "message_id": result.get("id"), "to": payload["to"], "subject": payload["subject"]}

    if approval.action_type == "reply_to_email":
        message_id = payload["message_id"]
        original = gmail_service.users().messages().get(
            userId="me", id=message_id, format="metadata",
            metadataHeaders=["From", "Subject", "Message-ID", "References"],
        ).execute()
        headers = {h["name"]: h["value"] for h in original.get("payload", {}).get("headers", [])}
        thread_id = original["threadId"]
        original_sender = parseaddr(headers.get("From", ""))[1]
        original_subject = headers.get("Subject", "")
        reply_subject = original_subject if original_subject.lower().startswith("re:") else f"Re: {original_subject}"
        original_message_id_header = headers.get("Message-ID", "")
        prior_references = headers.get("References", "")
        message = MIMEText(payload["body"])
        message["to"] = original_sender
        message["subject"] = reply_subject
        if original_message_id_header:
            message["In-Reply-To"] = original_message_id_header
            message["References"] = f"{prior_references} {original_message_id_header}".strip()
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        sent = gmail_service.users().messages().send(
            userId="me", body={"raw": raw, "threadId": thread_id}
        ).execute()
        return {"status": "replied", "message_id": sent.get("id"), "to": original_sender, "subject": reply_subject}

    if approval.action_type == "send_meeting_invite_email":
        message = MIMEText(payload["body"])
        message["to"] = payload["to"]
        message["subject"] = payload["subject"]
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        result = gmail_service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return {
            "status": "sent",
            "message_id": result.get("id"),
            "to": payload["to"],
            "subject": payload["subject"],
            "calendar_event_created": False,
        }

    if approval.action_type == "create_calendar_event":
        event = {
            "summary": payload["summary"],
            "description": payload.get("description", ""),
            "start": {"dateTime": payload["start_time"], "timeZone": settings.app_timezone},
            "end": {"dateTime": payload["end_time"], "timeZone": settings.app_timezone},
        }
        created = calendar_service.events().insert(calendarId="primary", body=event).execute()
        return {"status": "created", "event_id": created.get("id"), "link": created.get("htmlLink"), "summary": payload["summary"]}

    raise ValueError(f"Unsupported approval action: {approval.action_type}")
