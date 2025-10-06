import os
from pydantic import BaseModel

class Settings(BaseModel):
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "dev")
    TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Kolkata")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info")

    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_WEBHOOK_SECRET: str = os.getenv("TELEGRAM_WEBHOOK_SECRET", "change-me")
    PUBLIC_BASE_URL: str = os.getenv("PUBLIC_BASE_URL", "")

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    DATABASE_URL: str | None = os.getenv("DATABASE_URL") or None
    DB_PATH: str = os.getenv("DB_PATH", "sawmill_mvp.db")

    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "*")

settings = Settings()