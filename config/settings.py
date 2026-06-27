"""Application configuration with Pydantic settings."""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """All app settings loaded from environment or .env file."""

    # ── Database ──────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/aisdr"

    # ── Telegram Bot ─────────────────────────────────────────
    telegram_bot_token: str = ""
    telegram_admin_id: int = 0

    # ── AI (OpenAI-compatible — works with Kimi, OpenAI, DeepSeek) ──
    ai_api_key: str = ""
    ai_base_url: str = "https://api.moonshot.cn/v1"  # Kimi API
    ai_model: str = "moonshot-v1-8k"

    # ── External APIs ────────────────────────────────────────
    firecrawl_api_key: str = ""
    smartlead_api_key: str = ""
    smartlead_campaign_id: str = ""
    apollo_api_key: str = ""
    google_maps_api_key: str = ""  # For Places lead hunting

    # ── Google Sheets (optional review layer) ───────────────────
    google_sheets_credentials: str = ""  # path to service-account JSON
    google_sheet_id: str = ""

    # ── App ──────────────────────────────────────────────────
    app_env: str = "development"
    daily_email_limit: int = 100
    timezone: str = "UTC"
    followup_days: str = "3,7,14"  # comma-separated days for follow-ups

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
