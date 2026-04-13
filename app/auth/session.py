"""
session.py - Session and cookie management

Handles JWT token creation/validation and secure cookie operations.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt, JWTError
from fastapi import Response

from ..config import get_settings


# JWT configuration
ALGORITHM = "HS256"
COOKIE_NAME = "session"


class SessionError(Exception):
    """Raised when session validation fails."""
    pass


def create_session_token(
    github_id: int,
    username: str,
    name: Optional[str],
    avatar_url: str,
) -> str:
    """
    Create a signed JWT session token.
    
    Args:
        github_id: GitHub user ID
        username: GitHub username (login)
        name: Display name (may be None)
        avatar_url: User's avatar URL
        
    Returns:
        Signed JWT token string
    """
    settings = get_settings()
    
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.session_expire_hours)
    
    payload = {
        "sub": str(github_id),
        "username": username,
        "name": name or username,
        "avatar_url": avatar_url,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    
    return jwt.encode(payload, settings.session_secret_key, algorithm=ALGORITHM)


def decode_session_token(token: str) -> dict:
    """
    Decode and validate a session token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded payload dict with user info
        
    Raises:
        SessionError: If token is invalid or expired
    """
    settings = get_settings()
    
    try:
        payload = jwt.decode(
            token,
            settings.session_secret_key,
            algorithms=[ALGORITHM],
        )
        return payload
    except JWTError as e:
        raise SessionError(f"Invalid session token: {e}")


def set_session_cookie(response: Response, token: str) -> None:
    """
    Set the session cookie on a response.
    
    Args:
        response: FastAPI Response object
        token: JWT token to store in cookie
    """
    settings = get_settings()
    
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.is_production,  # Only require HTTPS in production
        samesite="lax",
        max_age=settings.session_expire_hours * 3600,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    """
    Remove the session cookie.
    
    Args:
        response: FastAPI Response object
    """
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
    )
