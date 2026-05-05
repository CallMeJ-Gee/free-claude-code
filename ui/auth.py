"""Authentication for admin UI."""

from typing import Annotated

import bcrypt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from config.settings import get_settings

security = HTTPBasic()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    if not hashed_password:
        return False
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def get_current_admin_user(
    credentials: HTTPBasicCredentials = Security(security)
) -> str:
    """Authenticate admin user. Returns username if valid."""
    settings = get_settings()

    # Admin UI is disabled
    if not settings.enable_admin_ui:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin UI is not enabled"
        )

    # Verify username
    if credentials.username != settings.admin_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Basic realm=\"Admin\""},
        )

    # Verify password hash
    if not verify_password(credentials.password, settings.admin_password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Basic realm=\"Admin\""},
        )

    return credentials.username


# Type alias for dependency injection
AdminUser = Annotated[str, Depends(get_current_admin_user)]
