from google.oauth2 import id_token # Google check if this login token is genuine.
from google.auth.transport import requests as google_requests # This is the messenger that talks to Google
from app.core.config import settings


def verify_google_token(token: str) -> dict:
    """
    The frontend sends us a token that Google issued after the user logged in
    with their Google account. We do NOT trust it blindly — we ask Google's
    own servers to confirm it's real and get the user's info back.

    This one function call is what actually stops someone from just sending
    us a fake token claiming to be any email they want.
    """
    idinfo = id_token.verify_oauth2_token(
        token, google_requests.Request(), settings.google_client_id
    )
    # idinfo now contains: sub (Google's unique user ID), email, name, picture
    return {
        "google_id": idinfo["sub"],
        "email": idinfo["email"],
        "name": idinfo.get("name", ""),
        "picture": idinfo.get("picture", ""),
    }


                # User
                #     │
                #     ▼
                # Clicks "Sign in with Google"
                #     │
                #     ▼
                # Google Login Screen
                #     │
                #     ▼
                # Google verifies user
                #     │
                #     ▼
                # Google creates an ID Token
                #     │
                #     ▼
                # React Frontend receives token
                #     │
                #     ▼
                # Frontend sends token to FastAPI
                #     │
                #     ▼
                # verify_google_token(token)
                #     │
                #     ▼
                # FastAPI asks Google:
                # "Is this token real?"
                #     │
                #     ▼
                # Google replies:
                # ✓ Yes
                #     or
                # ✗ No
                #     │
                #     ▼
                # If valid:
                # Extract user information
                #     │
                #     ▼
                # Return:
                # {
                #     "google_id": "...",
                #     "email": "...",
                #     "name": "...",
                #     "picture": "..."
                # }