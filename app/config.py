# app/config.py
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ENVIRONMENT: str = Field("prod", env="ENVIRONMENT")
    TIMEZONE: str = Field("Asia/Kolkata", env="TIMEZONE")
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")

    TELEGRAM_BOT_TOKEN: str = Field("", env="TELEGRAM_BOT_TOKEN")
    TELEGRAM_WEBHOOK_SECRET: str = Field("", env="TELEGRAM_WEBHOOK_SECRET")
    PUBLIC_BASE_URL: str = Field("", env="PUBLIC_BASE_URL")

    OPENAI_API_KEY: str = Field("", env="OPENAI_API_KEY")

    DATABASE_URL: str | None = Field(None, env="DATABASE_URL")
    DB_PATH: str = Field("sawmill_mvp.db", env="DB_PATH")

    RATE_LIMIT_PER_MINUTE: int = Field(60, env="RATE_LIMIT_PER_MINUTE")
    ALLOWED_ORIGINS: str = Field("*", env="ALLOWED_ORIGINS")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
