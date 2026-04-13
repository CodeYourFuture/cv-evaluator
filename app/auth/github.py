"""
github.py - GitHub OAuth client

Handles GitHub OAuth flow and API calls for user info and org membership.
"""

import httpx
import secrets
import logging
from typing import Optional
from dataclasses import dataclass

from ..config import get_settings

# Set up logging
logger = logging.getLogger(__name__)


# GitHub OAuth endpoints
GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API_URL = "https://api.github.com"


@dataclass
class GitHubUser:
    """GitHub user profile data."""
    id: int
    login: str
    name: Optional[str]
    email: Optional[str]
    avatar_url: str


class GitHubOAuthError(Exception):
    """Raised when GitHub OAuth flow fails."""
    pass


class OrgMembershipError(Exception):
    """Raised when user is not a member of the required organization."""
    pass


def generate_state() -> str:
    """Generate a random state parameter for CSRF protection."""
    return secrets.token_urlsafe(32)


def get_authorize_url(state: str) -> str:
    """
    Build the GitHub OAuth authorization URL.
    
    Args:
        state: CSRF protection token
        
    Returns:
        Full authorization URL to redirect user to
    """
    settings = get_settings()
    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": settings.oauth_callback_url,
        "scope": "read:user read:org",
        "state": state,
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{GITHUB_AUTHORIZE_URL}?{query}"


async def exchange_code_for_token(code: str) -> str:
    """
    Exchange authorization code for access token.
    
    Args:
        code: Authorization code from GitHub callback
        
    Returns:
        Access token string
        
    Raises:
        GitHubOAuthError: If token exchange fails
    """
    settings = get_settings()
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GITHUB_TOKEN_URL,
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
        
        if response.status_code != 200:
            raise GitHubOAuthError(f"Token exchange failed: {response.status_code}")
        
        data = response.json()
        logger.info(f"Token exchange response: {data}")
        
        # Log the granted scope (if present)
        scope = data.get("scope", "")
        logger.info(f"Granted scopes: {scope}")
        
        if "error" in data:
            raise GitHubOAuthError(f"Token exchange error: {data.get('error_description', data['error'])}")
        
        access_token = data.get("access_token")
        if not access_token:
            raise GitHubOAuthError("No access token in response")
        
        return access_token


async def get_user_info(access_token: str) -> GitHubUser:
    """
    Fetch user profile from GitHub API.
    
    Args:
        access_token: GitHub OAuth access token
        
    Returns:
        GitHubUser with profile data
        
    Raises:
        GitHubOAuthError: If API call fails
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GITHUB_API_URL}/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
        )
        
        if response.status_code != 200:
            raise GitHubOAuthError(f"Failed to fetch user info: {response.status_code}")
        
        data = response.json()
        
        return GitHubUser(
            id=data["id"],
            login=data["login"],
            name=data.get("name"),
            email=data.get("email"),
            avatar_url=data["avatar_url"],
        )


async def check_org_membership(access_token: str, org: str) -> bool:
    """
    Check if authenticated user is a member of the specified organization.
    
    Args:
        access_token: GitHub OAuth access token
        org: Organization name to check membership for
        
    Returns:
        True if user is a member, False otherwise
    """
    logger.info(f"Checking org membership for org: {org}")
    
    async with httpx.AsyncClient() as client:
        # Use the membership endpoint - returns 200 if member, 404 if not
        url = f"{GITHUB_API_URL}/user/memberships/orgs/{org}"
        logger.info(f"Requesting: {url}")
        
        response = await client.get(
            url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
        )
        
        logger.info(f"Membership check response status: {response.status_code}")
        logger.info(f"Membership check response body: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            state = data.get("state")
            logger.info(f"Membership state: {state}")
            # Check that membership is active
            return state == "active"
        
        return False


async def verify_org_membership(access_token: str) -> None:
    """
    Verify user is a member of the allowed organization.
    
    Args:
        access_token: GitHub OAuth access token
        
    Raises:
        OrgMembershipError: If user is not a member
    """
    settings = get_settings()
    logger.info(f"Verifying membership for org: {settings.allowed_org}")
    is_member = await check_org_membership(access_token, settings.allowed_org)
    logger.info(f"Membership check result: {is_member}")
    
    if not is_member:
        logger.warning(f"User is NOT a member of {settings.allowed_org}")
        raise OrgMembershipError(
            f"You must be a member of the {settings.allowed_org} organization to use this application."
        )
