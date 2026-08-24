import base64
from email.mime.text import MIMEText
from email.utils import parseaddr
import re
import requests
from bs4 import BeautifulSoup
from langchain_core.tools import tool
from googleapiclient.discovery import build
from ddgs import DDGS
from app.integrations.google_client import get_valid_credentials, save_refreshed_token
from app.agents.embeddings import embed_query
from app.db.models import DocumentChunk, Document, UserMemory, Approval
from app.services.document_service import extract_text as extract_document_text
from app.core.config import settings

MAX_URL_CONTENT_CHARS = 8000


def _extract_readable_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "form", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


def _create_approval(db, user, run_id: str | None, action_type: str, payload: dict) -> str:
    row = Approval(user_id=user.id, run_id=run_id, action_type=action_type, payload=payload)
    db.add(row)
    db.commit()
    db.refresh(row)
    return str(row.id)


def build_user_tools(user, db, conversation_id, run_id: str | None = None, remote_mcp_tools=None):
    """Build authenticated, user-scoped tools plus discovered MCP tools."""
    _services = None

    def _google_services():
        nonlocal _services
        if _services is not None:
            return _services
        if not user.google_access_token and not user.google_refresh_token:
            raise RuntimeError("Google services are not connected for this account. Connect Gmail/Calendar first.")
        creds = get_valid_credentials(user)
        save_refreshed_token(db, user, creds)
        _services = (
            build("gmail", "v1", credentials=creds),
            build("calendar", "v3", credentials=creds),
        )
        return _services

    @tool
    def send_email(to: str, subject: str, body: str) -> str:
        """Draft an email for approval. Use when the user explicitly wants an email sent. Never execute the send directly."""
        approval_id = _create_approval(db, user, run_id, "send_email", {"to": to, "subject": subject, "body": body})
        return f"EMAIL_APPROVAL_REQUIRED:{approval_id}:The email is drafted and waiting for approval. Do not claim it was sent."

    @tool
    def send_meeting_invite_email(to: str, subject: str, meeting_title: str, start_time: str, duration_minutes: int = 60, notes: str = "") -> str:
        """Send ONLY a meeting invitation email after approval. IMPORTANT: this tool NEVER creates or changes a Google Calendar event. Use it when the user says to invite someone by email only, explicitly says not to add a calendar event, or asks to send a meeting invite email."""
        body = (
            f"Hi,\n\nYou are invited to the following meeting:\n\n"
            f"Meeting: {meeting_title}\n"
            f"When: {start_time} ({settings.app_timezone})\n"
            f"Duration: {duration_minutes} minutes\n"
        )
        if notes.strip():
            body += f"\nNotes: {notes.strip()}\n"
        body += "\nPlease reply to confirm your availability.\n\nBest regards"
        approval_id = _create_approval(
            db, user, run_id, "send_meeting_invite_email",
            {"to": to, "subject": subject, "body": body, "meeting_title": meeting_title, "start_time": start_time, "duration_minutes": duration_minutes},
        )
        return f"MEETING_EMAIL_APPROVAL_REQUIRED:{approval_id}:A meeting invite email is drafted. No calendar event was created. Wait for approval before sending."

    @tool
    def list_recent_emails(max_results: int = 5, query: str = "") -> str:
        """List recent matching Gmail messages with message IDs, sender, subject and snippet."""
        gmail_service, _ = _google_services()
        result = gmail_service.users().messages().list(userId="me", maxResults=max(1, min(max_results, 20)), q=query or None).execute()
        message_ids = result.get("messages", [])
        if not message_ids:
            return "No matching emails found."
        lines = []
        for m in message_ids:
            msg = gmail_service.users().messages().get(userId="me", id=m["id"], format="metadata", metadataHeaders=["From", "Subject"]).execute()
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            lines.append(f"message_id: {m['id']} | From: {headers.get('From', 'unknown')} | Subject: {headers.get('Subject', '(no subject)')} | {msg.get('snippet', '')}")
        return "\n".join(lines)

    @tool
    def reply_to_email(message_id: str, body: str) -> str:
        """Draft a reply in the same Gmail thread. Approval is required before sending."""
        gmail_service, _ = _google_services()
        original = gmail_service.users().messages().get(userId="me", id=message_id, format="metadata", metadataHeaders=["From", "Subject"]).execute()
        headers = {h["name"]: h["value"] for h in original.get("payload", {}).get("headers", [])}
        approval_id = _create_approval(db, user, run_id, "reply_to_email", {"message_id": message_id, "body": body})
        return f"REPLY_APPROVAL_REQUIRED:{approval_id}:Draft reply to {headers.get('From', 'the sender')} is waiting for approval."

    @tool
    def create_calendar_event(summary: str, start_time: str, end_time: str, description: str = "") -> str:
        """Draft a Google Calendar event. Approval is required before creation. Use only when the user actually wants a calendar event created. when user says set up a meeting or create a meeting or schedule a meeting then use this tool"""
        approval_id = _create_approval(db, user, run_id, "create_calendar_event", {"summary": summary, "start_time": start_time, "end_time": end_time, "description": description})
        return f"CALENDAR_APPROVAL_REQUIRED:{approval_id}:The calendar event is waiting for user approval. Do not claim it was created."

    @tool
    def list_calendar_events(max_results: int = 5) -> str:
        """List the user's upcoming Google Calendar events."""
        import datetime as dt
        _, calendar_service = _google_services()
        now = dt.datetime.now(dt.timezone.utc).isoformat()
        result = calendar_service.events().list(calendarId="primary", timeMin=now, maxResults=max(1, min(max_results, 20)), singleEvents=True, orderBy="startTime").execute()
        events = result.get("items", [])
        if not events:
            return "No upcoming events found."
        return "\n".join(f"{e['start'].get('dateTime', e['start'].get('date'))} | {e.get('summary', '(no title)')}" for e in events)

    @tool
    def search_uploaded_documents(query: str, top_k: int = 6) -> str:
        """Search the user's uploaded documents for evidence relevant to the query. Use for questions about uploaded files. if user ask about uploaded documents then use this tool. and user my not mention the pdf name or file name use the pdf name from the conversation history"""
        vector = embed_query(query)
        rows = (
            db.query(DocumentChunk, Document)
            .join(Document, Document.id == DocumentChunk.document_id)
            .filter(Document.user_id == user.id, Document.conversation_id == conversation_id)
            .order_by(DocumentChunk.embedding.cosine_distance(vector))
            .limit(max(1, min(top_k, 12)))
            .all()
        )
        if not rows:
            return "No uploaded-document evidence was found for this conversation."
        parts = []
        for idx, (chunk, document) in enumerate(rows, 1):
            parts.append(f"[{idx}] {document.filename} | chunk {chunk.chunk_index}\n{chunk.content}")
        return "\n\n".join(parts)

    @tool
    def remember(fact: str) -> str:
        """Remember one useful, stable user preference or fact."""
        fact = fact.strip()
        if not fact:
            return "Nothing to remember."
        if len(fact) > 500:
            return "Memory is too long. Save one concise fact or preference."
        row = UserMemory(user_id=user.id, content=fact)
        db.add(row)
        db.commit()
        return f"Remembered: {fact}"

    @tool
    def forget_memory(fact_contains: str) -> str:
        """Delete durable memories containing the supplied phrase."""
        rows = db.query(UserMemory).filter(UserMemory.user_id == user.id, UserMemory.content.ilike(f"%{fact_contains.strip()}%")).all()
        if not rows:
            return "No matching memory found."
        for row in rows:
            db.delete(row)
        db.commit()
        return f"Deleted {len(rows)} matching memories."

    @tool
    def analyze_url(url: str) -> str:
        """Read the readable content of a specific public URL or PDF. Use when the user gives a URL."""
        try:
            response = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0 (compatible; ChatBot/1.0)"})
            response.raise_for_status()
        except Exception as exc:
            return f"Couldn't fetch that URL: {exc}"
        content_type = response.headers.get("Content-Type", "").lower()
        if "application/pdf" in content_type or url.lower().endswith(".pdf"):
            try:
                text = extract_document_text(response.content, "downloaded.pdf")
            except Exception as exc:
                return f"Found a PDF at that URL but couldn't read it: {exc}"
        else:
            text = _extract_readable_text(response.text)
        if not text:
            return "The URL loaded but contained no readable text."
        return text[:MAX_URL_CONTENT_CHARS] + ("\n\n[content truncated]" if len(text) > MAX_URL_CONTENT_CHARS else "")

    native = [
        send_email,
        send_meeting_invite_email,
        list_recent_emails,
        reply_to_email,
        create_calendar_event,
        list_calendar_events,
        search_uploaded_documents,
        remember,
        forget_memory,
        analyze_url,
    ]
    return native + list(remote_mcp_tools or [])
