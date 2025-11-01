"""
Core configuration module using Pydantic Settings.

This module centralizes all configuration management using environment variables
and provides type safety and validation.
"""

from functools import lru_cache

from pydantic import Field
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
    notion_output_database_id: str | None = Field(
        None,
        description="Notion database ID for storing generation records",
        env=["NOTION_OUTPUT_DATABASE_ID", "NOTION_DATABASE_ID"],
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
    blob_read_write_token: str | None = Field(
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
    public_base_url: str | None = Field(
        default=None,
        description="Public base URL used to build shareable preview links",
    )

    # Monitoring Configuration
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    metrics_endpoint: str = Field(
        default="/metrics", description="Metrics endpoint path"
    )

    # Backwards-compatible properties usados em testes
    @property
    def notion_api_token(self) -> str:
        return self.notion_token

    @property
    def notion_database_id(self) -> str | None:
        return self.notion_output_database_id

    @property
    def notion_fact_id(self) -> str | None:
        return self.notion_fact_database_id

    @property
    def notion_talhoes_id(self) -> str | None:
        return self.notion_talhoes_database_id

    @property
    def vercel_blob_token(self) -> str | None:
        return self.blob_read_write_token


# Helper para cachear settings
@lru_cache
def get_settings() -> Settings:
    return Settings()


# Global settings instance
settings = get_settings()
