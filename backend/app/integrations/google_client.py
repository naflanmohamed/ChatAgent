from datetime import datetime, timedelta, timezone
import requests
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
from google.oauth2.credentials import Credentials
from app.core.config import settings

TOKEN_URL = "https://oauth2.googleapis.com/token"

SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly",
]


def exchange_code_for_tokens(auth_code: str) -> dict:
    """
    Trades the one-time authorization code the frontend received from
    Google for real, usable tokens. This is a server-to-server call --
    it needs the client SECRET, which is why this can't happen in the
    browser. Returns Google's raw token response (access_token,
    refresh_token, id_token, expires_in, ...).
    """
    response = requests.post(
        TOKEN_URL,
        data={
            "code": auth_code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": "postmessage",
            "grant_type": "authorization_code",
        },
    )
    response.raise_for_status()
    return response.json()


def decode_identity_from_id_token(id_token_str: str) -> dict:
    """
    The token response above includes an id_token (identity info signed by
    Google) alongside the access_token (API permission). We still verify
    it, same as before, just sourced from the code exchange now instead of
    a separate one-off login call.
    """
    idinfo = google_id_token.verify_oauth2_token(
        id_token_str, google_requests.Request(), settings.google_client_id
    )
    return {
        "google_id": idinfo["sub"],
        "email": idinfo["email"],
        "name": idinfo.get("name", ""),
        "picture": idinfo.get("picture", ""),
    }


def get_valid_credentials(user) -> Credentials:
    """
    Builds a google-auth Credentials object for this user, refreshing the
    access token first if it's expired. Every Gmail/Calendar tool call
    goes through this -- it's the one place token refresh logic lives.
    """
    creds = Credentials(
        token=user.google_access_token,
        refresh_token=user.google_refresh_token,
        token_uri=TOKEN_URL,
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=SCOPES,
    )

    expired = (
        user.google_token_expiry is None
        or user.google_token_expiry <= datetime.now(timezone.utc)
    )
    if expired and creds.refresh_token:
        creds.refresh(google_requests.Request())

    return creds


def save_refreshed_token(db, user, creds: Credentials) -> None:
    user.google_access_token = creds.token
    if creds.expiry:
        user.google_token_expiry = creds.expiry.replace(tzinfo=timezone.utc)
    db.commit()


# | Token             | Simple meaning                 | Used for                     |
# | ----------------- | ------------------------------ | ---------------------------- |
# | **ID Token**      | "Who is this person?"          | Verify Google identity       |
# | **Access Token**  | "What can I access right now?" | Gmail/Calendar API           |
# | **Refresh Token** | "Give me a new access token"   | Refresh expired access token |


            #              React
            #                │
            #                ▼
            #             FastAPI
            #                │
            #         ┌──────┴──────┐
            #         ▼             ▼
            #       JWT         Google OAuth
            #         │             │
            #         ▼             ▼
            #     User auth    Google credentials
            #         │             │
            #         └──────┬──────┘
            #                ▼
            #            LangGraph
            #                │
            #                ▼
            #              Gemini
            #                │
            #     ┌──────────┼──────────┐
            #     ▼          ▼          ▼
            #  Gmail      Calendar    Chat
            #  Tools       Tools
            #     │          │
            #     ▼          ▼
            #  Google APIs