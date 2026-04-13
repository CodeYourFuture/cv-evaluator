"""
routes.py - Authentication endpoints

Handles GitHub OAuth flow: login, callback, logout, and user info.
"""

import logging
import secrets
from fastapi import APIRouter, Request, Response, HTTPException, status
from fastapi.responses import RedirectResponse

from ..config import get_settings
from .github import (
    generate_state,
    get_authorize_url,
    exchange_code_for_token,
    get_user_info,
    verify_org_membership,
    GitHubOAuthError,
    OrgMembershipError,
)
from .session import create_session_token, set_session_cookie, clear_session_cookie
from .middleware import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

OAUTH_STATE_COOKIE_NAME = "oauth_state"
OAUTH_STATE_MAX_AGE_SECONDS = 300


def set_oauth_state_cookie(response: Response, state: str, is_production: bool) -> None:
    """Bind OAuth state to the browser with a short-lived HttpOnly cookie."""
    response.set_cookie(
        key=OAUTH_STATE_COOKIE_NAME,
        value=state,
        httponly=True,
        secure=is_production,
        samesite="lax",
        max_age=OAUTH_STATE_MAX_AGE_SECONDS,
        path="/api/auth",
    )


def clear_oauth_state_cookie(response: Response) -> None:
    """Remove the OAuth state cookie after callback validation."""
    response.delete_cookie(
        key=OAUTH_STATE_COOKIE_NAME,
        path="/api/auth",
    )


@router.get("/login")
async def login(request: Request):
    """
    Initiate GitHub OAuth flow.
    
    Redirects the user to GitHub's authorization page.
    """
    settings = get_settings()
    
    if not settings.github_client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GitHub OAuth not configured. Set GITHUB_APP_CLIENT_ID environment variable.",
        )
    
    # Generate state for CSRF protection and bind it to this browser.
    state = generate_state()

    # Redirect to GitHub and set state cookie.
    auth_url = get_authorize_url(state)
    response = RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)
    set_oauth_state_cookie(response, state, settings.is_production)
    return response


@router.get("/callback")
async def callback(
    request: Request,
    code: str = None,
    state: str = None,
    error: str = None,
    error_description: str = None,
):
    """
    Handle GitHub OAuth callback.
    
    Exchanges authorization code for access token, verifies org membership,
    creates session, and redirects to app.
    """
    settings = get_settings()
    cookie_state = request.cookies.get(OAUTH_STATE_COOKIE_NAME)

    def _error_redirect(message: str) -> RedirectResponse:
        response = RedirectResponse(
            url=f"/?error={message}",
            status_code=status.HTTP_302_FOUND,
        )
        clear_oauth_state_cookie(response)
        return response
    
    # Handle OAuth errors from GitHub
    if error:
        logger.error(f"OAuth error from GitHub: {error} - {error_description}")
        return _error_redirect(error_description or error)
    
    # Validate required parameters
    if not code or not state:
        logger.error("Missing code or state in callback")
        return _error_redirect("Missing authorization code or state")
    
    # Verify state using cookie-bound one-time nonce.
    if not cookie_state or not secrets.compare_digest(state, cookie_state):
        logger.error("Invalid state parameter")
        return _error_redirect("Invalid state parameter. Please try logging in again.")
    
    try:
        # Exchange code for access token
        access_token = await exchange_code_for_token(code)
        
        # Get user info first (for logging)
        github_user = await get_user_info(access_token)
        logger.info(f"GitHub user: {github_user.login} (ID: {github_user.id})")
        
        # Verify organization membership
        await verify_org_membership(access_token)
        logger.info(f"User {github_user.login} is verified as org member")
        
        # Create session token
        session_token = create_session_token(
            github_id=github_user.id,
            username=github_user.login,
            name=github_user.name,
            avatar_url=github_user.avatar_url,
        )
        
        # Create redirect response and set cookie
        response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        set_session_cookie(response, session_token)
        clear_oauth_state_cookie(response)
        
        logger.info(f"Login successful for {github_user.login}")
        return response
        
    except OrgMembershipError as e:
        logger.warning(f"Org membership check failed: {e}")
        return _error_redirect("Access denied. You must be a member of the required organization.")
    except GitHubOAuthError as e:
        logger.error(f"GitHub OAuth error: {e}")
        return _error_redirect("Authentication failed. Please try signing in again.")
    except Exception as e:
        logger.exception(f"Unexpected error during OAuth callback: {e}")
        return _error_redirect("An unexpected error occurred. Please try again.")


@router.get("/logout")
async def logout(request: Request):
    """
    Log out the current user.
    
    Clears the session cookie and redirects to home page.
    """
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    clear_session_cookie(response)
    return response


@router.get("/me")
async def get_me(request: Request):
    """
    Get current user info.
    
    Returns user data if authenticated, 401 otherwise.
    Used by frontend to check auth state.
    """
    user = get_current_user(request)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    
    return {
        "github_id": user.github_id,
        "username": user.username,
        "name": user.name,
        "avatar_url": user.avatar_url,
    }
