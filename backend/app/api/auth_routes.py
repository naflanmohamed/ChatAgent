from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from app.integrations.google_client import exchange_code_for_tokens, decode_identity_from_id_token
from app.auth.dependencies import get_current_user
from app.core.security import create_access_token
from app.db.database import get_db
from app.db.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


class GoogleLoginRequest(BaseModel):
    code: str  # authorization code from the frontend's auth-code flow


@router.post("/google")
def google_login(body: GoogleLoginRequest, db: Session = Depends(get_db)):
    tokens = exchange_code_for_tokens(body.code)
    google_user = decode_identity_from_id_token(tokens["id_token"])

    user = db.query(User).filter(User.google_id == google_user["google_id"]).first()
    if user is None:
        user = User(
            google_id=google_user["google_id"],
            email=google_user["email"],
            name=google_user["name"],
            picture=google_user["picture"],
        )
        db.add(user)
    else:
        user.name = google_user["name"]
        user.picture = google_user["picture"]

    user.google_access_token = tokens["access_token"]
    user.google_token_expiry = datetime.now(timezone.utc) + timedelta(seconds=tokens.get("expires_in", 3600))
    if tokens.get("refresh_token"):
        user.google_refresh_token = tokens["refresh_token"]

    db.commit()
    db.refresh(user)

    access_token = create_access_token(user_id=user.id, email=user.email)

    return {
        "access_token": access_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "picture": user.picture,
        },
    }


@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return current_user
