"""Configuration management for AI Code Review Assistant."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # GitLab Configuration
    gitlab_url: str = Field(..., description="GitLab instance URL")
    gitlab_token: str = Field(..., description="GitLab personal access token")
    gitlab_webhook_secret: str = Field(..., description="Webhook secret for verification")

    # AI Provider Configuration
    ai_provider: Literal["openai", "anthropic", "azure"] = Field(
        default="anthropic", description="AI provider to use"
    )
    openai_api_key: str | None = Field(default=None, description="OpenAI API key")
    anthropic_api_key: str | None = Field(default=None, description="Anthropic API key")
    azure_openai_endpoint: str | None = Field(default=None, description="Azure OpenAI endpoint")
    azure_openai_api_key: str | None = Field(default=None, description="Azure OpenAI API key")

    # Model Configuration
    ai_model: str = Field(
        default="claude-3-5-sonnet-20241022",
        description="AI model to use for code review",
    )
    ai_temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        description="Temperature for AI model responses",
    )
    ai_max_tokens: int = Field(
        default=4096,
        ge=256,
        le=32768,
        description="Maximum tokens for AI responses",
    )

    # Application Settings
    app_env: Literal["development", "staging", "production"] = Field(
        default="development", description="Application environment"
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Logging level"
    )
    port: int = Field(default=8000, ge=1024, le=65535, description="Application port")
    host: str = Field(default="0.0.0.0", description="Application host")

    # Review Configuration
    max_diff_size: int = Field(
        default=10000,
        ge=100,
        description="Maximum number of lines to analyze in diff",
    )
    review_timeout: int = Field(
        default=300,
        ge=30,
        description="Review timeout in seconds",
    )
    min_files_for_review: int = Field(default=1, ge=1, description="Minimum files to trigger review")
    max_files_for_review: int = Field(default=50, ge=1, description="Maximum files to review")
    max_concurrent_reviews: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of concurrent file reviews",
    )
    min_test_coverage: int = Field(
        default=80,
        ge=0,
        le=100,
        description="Minimum test coverage percentage",
    )
    
    # HTTP Configuration
    http_timeout: float = Field(
        default=30.0,
        ge=5.0,
        le=120.0,
        description="HTTP request timeout in seconds",
    )

    # Feature Flags
    enable_security_scan: bool = Field(default=True, description="Enable security scanning")
    enable_performance_check: bool = Field(default=True, description="Enable performance checks")
    enable_style_check: bool = Field(default=True, description="Enable style checks")
    enable_auto_labeling: bool = Field(default=True, description="Enable automatic MR labeling")
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")

    # Database Configuration
    database_url: str | None = Field(
        default=None,
        description="Database URL for storing metrics and history",
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis URL for caching",
    )

    # Monitoring
    sentry_dsn: str | None = Field(default=None, description="Sentry DSN for error tracking")
    prometheus_enabled: bool = Field(default=True, description="Enable Prometheus metrics")

    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    max_requests_per_minute: int = Field(
        default=30,
        ge=1,
        description="Maximum requests per minute",
    )

    # Webhook
    webhook_secret: str = Field(..., description="Webhook secret for verification")
    webhook_verify_ssl: bool = Field(default=True, description="Verify SSL for webhooks")

    # Cache
    cache_enabled: bool = Field(default=True, description="Enable caching")
    cache_ttl: int = Field(default=3600, ge=60, description="Cache TTL in seconds")

    @field_validator("ai_provider")
    @classmethod
    def validate_ai_provider(cls, v: str, info) -> str:
        """Validate that the appropriate API key is set for the selected provider."""
        values = info.data
        if v == "openai" and not values.get("openai_api_key"):
            raise ValueError("openai_api_key must be set when using OpenAI provider")
        if v == "anthropic" and not values.get("anthropic_api_key"):
            raise ValueError("anthropic_api_key must be set when using Anthropic provider")
        if v == "azure" and (
            not values.get("azure_openai_endpoint") or not values.get("azure_openai_api_key")
        ):
            raise ValueError("Azure OpenAI endpoint and API key must be set when using Azure provider")
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
