from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support.

    NOTE:
    - The 'notion_token' environment variable must be set and have at least 50 characters.
    - The 'notion_fact_database_id' and 'notion_talhoes_database_id' environment variables must be at least 32 characters long.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    notion_token: str = Field(
        ...,
        description="Notion integration token",
        min_length=50,
        env="NOTION_TOKEN",
    )
    notion_output_database_id: str | None = Field(
        None,
        description="Notion database ID for storing generation records",
        env="NOTION_OUTPUT_DATABASE_ID",
    )
    notion_fact_database_id: str = Field(
        ...,
        description="Notion Fact Database ID (must be at least 32 characters)",
        min_length=32,
        env="NOTION_FACT_DATABASE_ID",
    )
    notion_talhoes_database_id: str = Field(
        ...,
        description="Notion Talhoes Database ID (must be at least 32 characters)",
        min_length=32,
        env="NOTION_TALHOES_DATABASE_ID",
    )
    log_level: str = Field(
        default="DEBUG", description="Logging level", env="LOG_LEVEL"
    )

    # API Configuration
    api_title: str = Field(default="Notion Backend API", description="API title")
    api_description: str = Field(
        default="API para processamento de webhooks do Notion e geração de relatórios PDF",
        description="API description",
    )
    api_version: str = Field(default="1.0.0", description="API version")

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
