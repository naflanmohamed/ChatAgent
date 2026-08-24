from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.auth.dependencies import get_current_user
from app.db.database import get_db
from app.db.models import Approval, AgentRun, User
from app.schemas.approval import ApprovalDecision, ApprovalOut
from app.services.action_service import execute_approved_action

router = APIRouter(prefix="/approvals", tags=["approvals"])


def _to_out(row: Approval):
    run = row.run_id
    return ApprovalOut(
        id=str(row.id), run_id=str(run), action_type=row.action_type,
        payload=row.payload, status=row.status, decision_note=row.decision_note,
        created_at=row.created_at, decided_at=row.decided_at,
    )


@router.get("", response_model=list[ApprovalOut])
def pending_approvals(
    conversation_id: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Approval).join(AgentRun, AgentRun.id == Approval.run_id).filter(
        Approval.user_id == current_user["user_id"],
        Approval.status == "pending",
    )
    if conversation_id:
        query = query.filter(AgentRun.conversation_id == conversation_id)
    rows = query.order_by(Approval.created_at.desc()).all()
    return [_to_out(r) for r in rows]


@router.post("/{approval_id}/approve", response_model=ApprovalOut)
def approve(approval_id: str, body: ApprovalDecision, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(Approval).filter(Approval.id == approval_id, Approval.user_id == current_user["user_id"]).first()
    if row is None:
        raise HTTPException(404, "Approval not found")
    if row.status != "pending":
        raise HTTPException(409, f"Approval is already {row.status}")
    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    if user is None:
        raise HTTPException(404, "User not found")
    if body.edited_payload is not None:
        row.payload = body.edited_payload
    try:
        result = execute_approved_action(db, user, row)
        row.status = "approved"
        row.decision_note = body.note or "Approved by user"
        row.decided_at = datetime.now(timezone.utc)
        db.commit()
        return _to_out(row)
    except Exception as exc:
        db.rollback()
        row = db.query(Approval).filter(Approval.id == approval_id).first()
        if row:
            row.status = "failed"
            row.decision_note = str(exc)
            row.decided_at = datetime.now(timezone.utc)
            db.commit()
        raise HTTPException(502, f"Action failed: {exc}")


@router.post("/{approval_id}/reject", response_model=ApprovalOut)
def reject(approval_id: str, body: ApprovalDecision, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(Approval).filter(Approval.id == approval_id, Approval.user_id == current_user["user_id"]).first()
    if row is None:
        raise HTTPException(404, "Approval not found")
    if row.status != "pending":
        raise HTTPException(409, f"Approval is already {row.status}")
    row.status = "rejected"
    row.decision_note = body.note or "Rejected by user"
    row.decided_at = datetime.now(timezone.utc)
    db.commit()
    return _to_out(row)
