"""
routes.py - Authentication endpoints

Handles GitHub OAuth flow: login, callback, logout, and user info.
"""

import logging
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

# Store state tokens temporarily
# For simplicity, we use an in-memory dict with the state as key
# This is cleared on server restart, which is acceptable for this use case
_oauth_states: dict[str, bool] = {}


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
    
    # Generate and store state for CSRF protection
    state = generate_state()
    _oauth_states[state] = True
    
    # Redirect to GitHub
    auth_url = get_authorize_url(state)
    return RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)


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
    logger.info("OAuth callback received")
    
    # Handle OAuth errors from GitHub
    if error:
        logger.error(f"OAuth error from GitHub: {error} - {error_description}")
        return RedirectResponse(
            url=f"/?error={error_description or error}",
            status_code=status.HTTP_302_FOUND,
        )
    
    # Validate required parameters
    if not code or not state:
        logger.error("Missing code or state in callback")
        return RedirectResponse(
            url="/?error=Missing authorization code or state",
            status_code=status.HTTP_302_FOUND,
        )
    
    # Verify state to prevent CSRF
    if state not in _oauth_states:
        logger.error("Invalid state parameter")
        return RedirectResponse(
            url="/?error=Invalid state parameter. Please try logging in again.",
            status_code=status.HTTP_302_FOUND,
        )
    
    # Remove used state
    del _oauth_states[state]
    
    try:
        # Exchange code for access token
        logger.info("Exchanging code for access token...")
        access_token = await exchange_code_for_token(code)
        logger.info("Got access token successfully")
        
        # Get user info first (for logging)
        github_user = await get_user_info(access_token)
        logger.info(f"GitHub user: {github_user.login} (ID: {github_user.id})")
        
        # Verify organization membership
        logger.info(f"Verifying org membership for user {github_user.login}...")
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
        
        logger.info(f"Login successful for {github_user.login}")
        return response
        
    except OrgMembershipError as e:
        logger.warning(f"Org membership check failed: {e}")
        return RedirectResponse(
            url=f"/?error={str(e)}",
            status_code=status.HTTP_302_FOUND,
        )
    except GitHubOAuthError as e:
        logger.error(f"GitHub OAuth error: {e}")
        return RedirectResponse(
            url=f"/?error=Authentication failed: {str(e)}",
            status_code=status.HTTP_302_FOUND,
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/?error=An unexpected error occurred: {str(e)}",
            status_code=status.HTTP_302_FOUND,
        )


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
