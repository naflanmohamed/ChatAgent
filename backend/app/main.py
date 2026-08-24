import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api import (
    auth_routes,
    chat_routes,
    conversation_routes,
    document_routes,
    approval_routes,
)

from app.db.database import Base, engine
from app.db import redis_client
from app.db import models
from app.core.config import settings


app = FastAPI(
    title="ChatBot Agentic Workspace",
    version="2.0.0",
    description="Gemini + LangGraph + RAG + Gmail + Calendar + MCP personal AI workspace.",
)


# Enable pgvector
with engine.connect() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    conn.commit()


# Create all SQLAlchemy tables
Base.metadata.create_all(bind=engine)


# Add new columns to existing tables
with engine.connect() as conn:
    conn.execute(
        text(
            "ALTER TABLE conversations "
            "ADD COLUMN IF NOT EXISTS "
            "model VARCHAR(100) NOT NULL "
            "DEFAULT 'gemini-2.5-flash'"
        )
    )
    conn.commit()


FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

if FRONTEND_URL not in allowed_origins:
    allowed_origins.append(FRONTEND_URL)


app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_routes.router)
app.include_router(chat_routes.router)
app.include_router(conversation_routes.router)
app.include_router(document_routes.router)
app.include_router(approval_routes.router)


@app.get("/health")
def health_check():
    checks = {
        "database": "unknown",
        "redis": "unknown",
    }

    overall = "ok"

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        checks["database"] = "ok"

    except Exception as exc:
        checks["database"] = f"error: {type(exc).__name__}"
        overall = "degraded"

    try:
        redis_client.redis_client.ping()
        checks["redis"] = "ok"

    except Exception as exc:
        checks["redis"] = f"error: {type(exc).__name__}"
        overall = "degraded"

    return {
        "status": overall,
        "service": "chatagent-backend",
        "mcp_enabled": settings.mcp_enabled,
        "checks": checks,
    }
