"""
config.py - Centralized application settings

Uses Pydantic BaseSettings for environment variable loading with validation.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # OpenRouter API (existing)
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    
    # GitHub OAuth
    github_client_id: str = Field(default="", alias="GITHUB_APP_CLIENT_ID")
    github_client_secret: str = Field(default="", alias="GITHUB_APP_CLIENT_SECRET")
    
    # Session security
    session_secret_key: str = Field(default="", alias="SESSION_SECRET_KEY")
    session_expire_hours: int = Field(default=24, alias="SESSION_EXPIRE_HOURS")
    
    # Organization restriction
    allowed_org: str = Field(default="CodeYourFuture", alias="ALLOWED_ORG")
    
    # Application URL (for OAuth callback)
    app_url: str = Field(default="http://localhost:8000", alias="APP_URL")
    
    # Environment
    environment: str = Field(default="development", alias="ENVIRONMENT")
    
    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"
    
    @property
    def oauth_callback_url(self) -> str:
        return f"{self.app_url}/api/auth/callback"
    
    @property
    def cors_origins(self) -> list[str]:
        if self.is_production:
            return [self.app_url]
        return ["*"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
