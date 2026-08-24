from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ApprovalOut(BaseModel):
    id: str
    run_id: str
    action_type: str
    payload: dict
    status: str
    decision_note: str | None = None
    created_at: datetime
    decided_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ApprovalDecision(BaseModel):
    note: str | None = None
    edited_payload: dict | None = None
