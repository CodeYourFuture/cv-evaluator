"""
middleware.py - Authentication middleware and dependencies

Provides FastAPI dependencies for route protection.
"""

from typing import Optional
from dataclasses import dataclass
from fastapi import Request, HTTPException, status

from .session import decode_session_token, SessionError, COOKIE_NAME


@dataclass
class User:
    """Authenticated user data extracted from session."""
    github_id: int
    username: str
    name: str
    avatar_url: str


def get_current_user(request: Request) -> Optional[User]:
    """
    Extract current user from session cookie if present.
    
    This is a "soft" auth check - returns None if not authenticated.
    Use require_auth for protected routes.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        User object if authenticated, None otherwise
    """
    token = request.cookies.get(COOKIE_NAME)
    
    if not token:
        return None
    
    try:
        payload = decode_session_token(token)
        return User(
            github_id=int(payload["sub"]),
            username=payload["username"],
            name=payload["name"],
            avatar_url=payload["avatar_url"],
        )
    except (SessionError, KeyError, ValueError):
        return None


def require_auth(request: Request) -> User:
    """
    FastAPI dependency that requires authentication.
    
    Use as a dependency on protected routes:
        @app.get("/protected")
        async def protected_route(user: User = Depends(require_auth)):
            ...
    
    Args:
        request: FastAPI Request object
        
    Returns:
        User object
        
    Raises:
        HTTPException: 401 if not authenticated
    """
    user = get_current_user(request)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in with GitHub.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user
