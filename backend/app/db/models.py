import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.db.database import Base


EMBEDDING_DIM = 768


def new_uuid():
    return str(uuid.uuid4())


def now_utc():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    google_id = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False)
    name = Column(String)
    picture = Column(String)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    google_access_token = Column(Text, nullable=True)
    google_refresh_token = Column(Text, nullable=True)
    google_token_expiry = Column(DateTime(timezone=True), nullable=True)

    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    memories = relationship("UserMemory", back_populates="user", cascade="all, delete-orphan")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, default="New Chat")
    model = Column(String, nullable=False, default="gemini-2.5-flash")
    created_at = Column(DateTime(timezone=True), default=now_utc)

    user = relationship("User", back_populates="conversations")
    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan",
        order_by="Message.created_at",
    )
    documents = relationship("Document", back_populates="conversation", cascade="all, delete-orphan", order_by="Document.uploaded_at.desc()")


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    conversation_id = Column(UUID(as_uuid=False), ForeignKey("conversations.id"), nullable=False, index=True)
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    conversation = relationship("Conversation", back_populates="messages")


class UserMemory(Base):
    __tablename__ = "user_memories"

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)  # one durable fact/preference, in plain English
    created_at = Column(DateTime(timezone=True), default=now_utc)

    user = relationship("User", back_populates="memories")


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False, index=True)
    conversation_id = Column(UUID(as_uuid=False), ForeignKey("conversations.id"), nullable=False, index=True)
    filename = Column(String, nullable=False)
    uploaded_at = Column(DateTime(timezone=True), default=now_utc)

    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    conversation = relationship("Conversation", back_populates="documents")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    document_id = Column(UUID(as_uuid=False), ForeignKey("documents.id"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)  # position within the document, for citations
    content = Column(Text, nullable=False)
    embedding = Column(Vector(EMBEDDING_DIM), nullable=False)

    document = relationship("Document", back_populates="chunks")


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    conversation_id = Column(UUID(as_uuid=False), ForeignKey("conversations.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False, index=True)
    goal = Column(Text, nullable=False)
    status = Column(String, default="running", nullable=False, index=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), default=now_utc)
    finished_at = Column(DateTime(timezone=True), nullable=True)


class ToolCallRecord(Base):
    __tablename__ = "tool_call_records"

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    run_id = Column(UUID(as_uuid=False), ForeignKey("agent_runs.id"), nullable=False, index=True)
    tool_name = Column(String, nullable=False, index=True)
    arguments = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    status = Column(String, default="completed", nullable=False)
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc)


class Approval(Base):
    __tablename__ = "approvals"

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    run_id = Column(UUID(as_uuid=False), ForeignKey("agent_runs.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False, index=True)
    action_type = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(String, default="pending", nullable=False, index=True)
    decision_note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc)
    decided_at = Column(DateTime(timezone=True), nullable=True)
