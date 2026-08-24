from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security import decode_access_token

# This tells FastAPI to look for "Authorization: Bearer <token>" in the request headers.
bearer_scheme = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    """
    A FastAPI "dependency". Any route that wants to require login just adds
    this as a parameter, and FastAPI runs it BEFORE the route's own code.
    If it raises an exception, the route function never even runs.
    """
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return {"user_id": payload["sub"], "email": payload["email"]}


        # Incoming Request
        #       │
        #       ▼
        # HTTPBearer
        #       │
        # Extract JWT
        #       │
        #       ▼
        # get_current_user()
        #       │
        #       ▼
        # decode_access_token()
        #       │
        #       ▼
        # JWT valid?
        #       │
        #   ├── No
        #   │      ▼
        #   │   Return 401
        #   │
        #   └── Yes
        #          ▼
        # Return user information
        #          ▼
        # profile(user)
        #          ▼
        # Return response