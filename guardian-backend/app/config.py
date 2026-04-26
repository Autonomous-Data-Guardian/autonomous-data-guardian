from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "Autonomous Data Guardian API"
    openmetadata_base_url: str = "http://localhost:8585"
    openmetadata_jwt_token: str = ""
    openmetadata_mcp_url: str = "http://localhost:8585/mcp"
    report_store_path: str = "reports.json"
    llm_enabled: bool = False
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_api_key: str = ""
    openrouter_model: str = "google/gemma-4-31b-it:free"
    openrouter_max_retries_per_key: int = 2
    openrouter_base_backoff_seconds: float = 0.8
    openrouter_max_tokens: int = 220
    csv_import_max_file_size_bytes: int = 5_000_000
    csv_import_database_url: str = "sqlite:///data/csv_imports.db"
    csv_import_openmetadata_database_schema_fqn: str = ""
    frontend_origin: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="GUARDIAN_", extra="ignore")


settings = Settings()
