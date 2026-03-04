"""Application configuration via Pydantic Settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM keys
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Model tiers
    primary_model: str = "claude-sonnet-4-20250514"
    fallback_model: str = "gpt-4o"
    cheap_model: str = "gpt-4o-mini"

    # Database
    database_url: str = "sqlite:///./elicit.db"

    # App
    app_env: str = "development"
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
