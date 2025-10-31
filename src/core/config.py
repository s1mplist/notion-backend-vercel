"""
Core configuration module using Pydantic Settings.

This module centralizes all configuration management using environment variables
and provides type safety and validation.
"""

from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file="environments/.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Notion API Configuration
    notion_token: str = Field(..., description="Notion API token", min_length=50)
    notion_output_database_id: Optional[str] = Field(
        None, description="Notion database ID for storing generation records"
    )

    notion_fact_database_id: str = Field(
        ..., description="Notion Fact Database ID", min_length=32
    )
    notion_talhoes_database_id: str = Field(
        ..., description="Notion Talhoes Database ID", min_length=32
    )

    # Logging Configuration
    log_level: str = Field(default="DEBUG", description="Logging level")

    # API Configuration
    api_title: str = Field(default="Notion Backend API", description="API title")
    api_description: str = Field(
        default="API para processamento de webhooks do Notion e geração de relatórios PDF",
        description="API description",
    )
    api_version: str = Field(default="1.0.0", description="API version")

    # Rate Limiting Configuration
    rate_limit_requests: int = Field(
        default=100, description="Maximum requests per window", gt=0
    )
    rate_limit_window: int = Field(
        default=60, description="Rate limit window in seconds", gt=0
    )

    # Vercel Blob Configuration
    blob_read_write_token: Optional[str] = Field(
        None, description="Vercel Blob storage token"
    )

    # HTML Rendering / Audit
    enable_html_audit: bool = Field(
        default=False,
        description="Enable detailed HTML audit logs (debug only)",
    )
    html_audit_max_chars: int = Field(
        default=12000,
        description="Max characters of HTML to include in audit logs",
        gt=1000,
    )

    # Public Base URL for shareable links (e.g., https://your-app.vercel.app)
    public_base_url: Optional[str] = Field(
        default=None,
        description="Public base URL used to build shareable preview links",
    )

    # Monitoring Configuration
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    metrics_endpoint: str = Field(
        default="/metrics", description="Metrics endpoint path"
    )

    @field_validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()

    @field_validator("notion_token")
    def validate_notion_token(cls, v):
        """Validate Notion token format."""
        if not v.startswith(("ntn_", "secret_")):
            raise ValueError('Notion token must start with "ntn_" or "secret_"')
        return v


# Global settings instance
settings = Settings()
