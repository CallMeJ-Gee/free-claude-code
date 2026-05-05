"""Session-based authentication for admin UI."""

from typing import Annotated
from datetime import datetime, timedelta
import secrets

from fastapi import Depends, HTTPException, Request, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import bcrypt

from config.settings import get_settings

security = HTTPBasic()

# Simple in-memory session store (in production, use Redis or database)
_sessions = {}

SESSION_COOKIE_NAME = "admin_session"
SESSION_DURATION = timedelta(hours=24)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    if not hashed_password:
        return False
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def create_session(username: str) -> str:
    """Create a new session for the user."""
    session_id = secrets.token_urlsafe(32)
    _sessions[session_id] = {
        "username": username,
        "created_at": datetime.now(),
        "expires_at": datetime.now() + SESSION_DURATION,
    }
    return session_id


def get_session(request: Request) -> dict | None:
    """Get the current session from the request."""
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        return None

    session = _sessions.get(session_id)
    if not session:
        return None

    # Check if session is expired
    if datetime.now() > session["expires_at"]:
        del _sessions[session_id]
        return None

    return session


def require_session(request: Request) -> str:
    """Require a valid session and return the username."""
    session = get_session(request)
    if not session:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Basic"},
        )
    return session["username"]


def get_current_admin_user(
    request: Request,
    response: Response,
    credentials: HTTPBasicCredentials | None = Depends(security),
) -> str:
    """Authenticate admin user. Returns username if valid."""
    settings = get_settings()

    # Admin UI is disabled
    if not settings.enable_admin_ui:
        raise HTTPException(
            status_code=404,
            detail="Admin UI is not enabled"
        )

    # Check for existing session first
    session = get_session(request)
    if session:
        return session["username"]

    # If no session, try Basic Auth
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Basic"},
        )

    # Verify username
    if credentials.username != settings.admin_user:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Basic"},
        )

    # Verify password hash
    if not verify_password(credentials.password, settings.admin_password_hash):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Basic"},
        )

    # Create session and set cookie
    session_id = create_session(credentials.username)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        session_id,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=int(SESSION_DURATION.total_seconds()),
    )

    return credentials.username


# Type alias for dependency injection
AdminUser = Annotated[str, Depends(get_current_admin_user)]
