"""
auth - GitHub OAuth authentication module

Provides GitHub OAuth authentication with organization membership verification.
"""

from .middleware import get_current_user, require_auth, User
from .routes import router as auth_router

__all__ = ["get_current_user", "require_auth", "User", "auth_router"]
