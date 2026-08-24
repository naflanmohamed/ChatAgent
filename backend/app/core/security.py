from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from app.core.config import settings


def create_access_token(user_id: str, email: str) -> str:
    """
    Builds our own login token after we've already verified the user via Google.
    A JWT is just a signed JSON blob — anyone can READ it, but only we can
    create a valid one, because only we know jwt_secret used to sign it.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": user_id, "email": email, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """
    Reverses create_access_token. Raises JWTError if the token is expired,
    tampered with, or signed with a different secret.
    """
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise ValueError("Invalid or expired token")


    # User
    #    │
    #    ▼
    # Logs in with Google
    #    │
    #    ▼
    # Google returns ID Token
    #    │
    #    ▼
    # Backend verifies Google Token
    #    │
    #    ▼
    # Backend creates its own JWT
    #    │
    #    ▼
    # JWT sent to frontend
    #    │
    #    ▼
    # Frontend stores JWT
    #    │
    #    ▼
    # Every future API request:
    # Authorization: Bearer <JWT>
    #    │
    #    ▼
    # Backend decodes JWT
    #    │
    #    ▼
    # Valid?
    #  ├── Yes → Allow request
    #  └── No  → Return 401 Unauthorized


# Google ID Token: "Google confirms this person's identity."
# Your JWT: "Your application confirms this user is logged in and allowed to use your APIs."