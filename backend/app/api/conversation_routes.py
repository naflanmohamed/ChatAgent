from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.model_registry import is_supported_model
from app.auth.dependencies import get_current_user
from app.db.database import get_db
from app.db.models import Conversation
from app.db import redis_client
from app.schemas.chat import ConversationOut, ConversationDetailOut

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", response_model=ConversationOut)
def create_conversation(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    conversation = Conversation(user_id=current_user["user_id"], title="New Chat")
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.get("", response_model=list[ConversationOut])
def list_conversations(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user["user_id"])
        .order_by(Conversation.created_at.desc())
        .all()
    )


@router.get("/{conversation_id}", response_model=ConversationDetailOut)
def get_conversation(conversation_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == current_user["user_id"])
        .first()
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.delete("/{conversation_id}")
def delete_conversation(conversation_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == current_user["user_id"])
        .first()
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(conversation)
    db.commit()
    redis_client.invalidate_cache(conversation_id)
    return {"status": "deleted"}


class ConversationModelUpdate(BaseModel):
    model: str


@router.patch("/{conversation_id}/model", response_model=ConversationOut)
def update_conversation_model(conversation_id: str, body: ConversationModelUpdate, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if not is_supported_model(body.model):
        raise HTTPException(status_code=400, detail="Unsupported model")
    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == current_user["user_id"])
        .first()
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conversation.model = body.model
    db.commit()
    db.refresh(conversation)
    return conversation
