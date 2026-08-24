from datetime import datetime, timezone
import re
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from app.auth.dependencies import get_current_user
from app.agents.graph import build_graph
from app.agents.tools import build_user_tools
from app.agents.title_agent import generate_title
from app.mcp.client import load_remote_mcp_tools
from app.db.database import get_db
from app.db.models import Conversation, Message, User, UserMemory, AgentRun, ToolCallRecord, Approval
from app.db import redis_client
from app.core.errors import classify_ai_error
from app.core.config import settings
from app.core.model_registry import get_model_options, is_supported_model
import time

router = APIRouter(tags=["chat"])
MAX_CONTEXT_MESSAGES = 24


class ChatRequest(BaseModel):
    conversation_id: str
    message: str
    model: str | None = None


@router.get("/models")
def list_models():
    return {"models": get_model_options(), "default": settings.default_gemini_model}


def _extract_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts) if parts else str(content)
    return str(content)


def _load_history(conversation_id: str, db: Session) -> list[dict]:
    cached = redis_client.get_cached_messages(conversation_id)
    if cached is not None:
        return cached
    messages = db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.created_at).all()
    history = [{"role": m.role, "content": m.content} for m in messages]
    redis_client.set_cached_messages(conversation_id, history)
    return history


def _to_langchain_messages(history: list[dict]) -> list:
    return [HumanMessage(content=m["content"]) if m["role"] == "user" else AIMessage(content=m["content"]) for m in history]


def _jsonable(value):
    return value if isinstance(value, dict) else {"raw": str(value)}


@router.post("/chat")
def chat(body: ChatRequest, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    conversation = db.query(Conversation).filter(
        Conversation.id == body.conversation_id,
        Conversation.user_id == current_user["user_id"],
    ).first()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    selected_model = body.model or conversation.model or settings.default_gemini_model
    if not is_supported_model(selected_model):
        raise HTTPException(status_code=400, detail="Unsupported model")
    conversation.model = selected_model
    is_first_message = len(conversation.messages) == 0

    history = _load_history(body.conversation_id, db)
    user_text = body.message
    intent_text = user_text
    # Strong application-level intent hint for the common meeting-email-only request.
    # This is deliberately added outside the model prompt so tool selection remains
    # consistent even when the user's wording is ambiguous.
    email_only = bool(re.search(r"(?:email only|only (?:send|sending) (?:an )?email|do not add.*calendar|without (?:adding|creating).*calendar)", user_text, re.I))
    if email_only:
        try:
            now_local = datetime.now(ZoneInfo(settings.app_timezone))
            intent_text += (
                "\n\n[APPLICATION INTENT: EMAIL-ONLY MEETING INVITE. "
                f"Resolved local date is {now_local.strftime('%Y-%m-%d')}. "
                "Do NOT call create_calendar_event. Use send_meeting_invite_email, then wait for approval.]"
            )
        except Exception:
            intent_text += "\n\n[APPLICATION INTENT: EMAIL-ONLY MEETING INVITE. Do NOT create a calendar event.]"

    lc_messages = _to_langchain_messages(history[-MAX_CONTEXT_MESSAGES:]) + [HumanMessage(content=intent_text)]

    run = AgentRun(conversation_id=conversation.id, user_id=user.id, goal=body.message, status="running")
    db.add(run)
    db.commit()
    db.refresh(run)

    started = time.perf_counter()
    try:
        remote_mcp_tools = []
        if settings.mcp_enabled and settings.mcp_server_url:
            try:
                remote_mcp_tools = load_remote_mcp_tools(settings.mcp_server_url)
            except Exception as exc:
                print(f"[mcp] discovery unavailable: {exc}")

        tools = build_user_tools(user, db, body.conversation_id, run_id=str(run.id), remote_mcp_tools=remote_mcp_tools)
        memories = db.query(UserMemory).filter(UserMemory.user_id == user.id).order_by(UserMemory.created_at.desc()).limit(20).all()
        graph = build_graph(tools, user_memories=[m.content for m in memories], model=selected_model)
        result = graph.invoke({"messages": lc_messages})
        duration = int((time.perf_counter() - started) * 1000)

        for msg in result.get("messages", []):
            calls = getattr(msg, "tool_calls", None)
            if calls:
                for call in calls:
                    db.add(ToolCallRecord(run_id=run.id, tool_name=call.get("name", "unknown"), arguments=_jsonable(call.get("args", {})), status="requested", duration_ms=duration))
            elif isinstance(msg, ToolMessage):
                db.add(ToolCallRecord(run_id=run.id, tool_name=getattr(msg, "name", None) or "tool", result={"content": _extract_text(msg.content)}, status="completed", duration_ms=duration))

        reply_text = _extract_text(result["messages"][-1].content)
        approvals = db.query(Approval).filter(Approval.run_id == run.id, Approval.status == "pending").all()

        db.add(Message(conversation_id=conversation.id, role="user", content=body.message))
        db.add(Message(conversation_id=conversation.id, role="assistant", content=reply_text))
        new_title = None
        if is_first_message:
            try:
                new_title = generate_title(body.message)
                conversation.title = new_title
            except Exception:
                new_title = None

        run.status = "waiting_approval" if approvals else "completed"
        if not approvals:
            run.finished_at = datetime.now(timezone.utc)
        db.commit()
        redis_client.set_cached_messages(body.conversation_id, history + [{"role": "user", "content": body.message}, {"role": "assistant", "content": reply_text}])

        return {
            "reply": reply_text,
            "title": new_title,
            "run_id": str(run.id),
            "status": run.status,
            "model": selected_model,
            "model_provider": "groq" if selected_model in {"openai/gpt-oss-120b", "llama-3.1-8b-instant"} else "gemini",
            "approvals": [{"id": str(a.id), "action_type": a.action_type, "payload": a.payload, "status": a.status} for a in approvals],
            "tool_count": len([m for m in result.get("messages", []) if getattr(m, "tool_calls", None)]) + len([m for m in result.get("messages", []) if isinstance(m, ToolMessage)]),
        }
    except Exception as exc:
        run.status = "failed"
        run.error = str(exc)
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        print(f"[chat_routes] AI call failed: {exc}")
        status_code, friendly_message = classify_ai_error(exc)
        raise HTTPException(status_code=status_code, detail=friendly_message)
