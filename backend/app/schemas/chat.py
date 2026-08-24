from datetime import datetime
from pydantic import BaseModel, ConfigDict


class MessageOut(BaseModel):
    role: str
    content: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ConversationOut(BaseModel):
    id: str
    title: str
    model: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ConversationDetailOut(ConversationOut):
    messages: list[MessageOut]
