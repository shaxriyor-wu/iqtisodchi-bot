from functools import lru_cache
from typing import Annotated
from zoneinfo import ZoneInfo

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bot_token: str
    # Faqat shular foydalana oladi. Ikkalasi bo'sh bo'lsa bot hech kimga javob bermaydi.
    allowed_usernames: Annotated[list[str], NoDecode] = []
    allowed_user_ids: Annotated[list[int], NoDecode] = []

    postgres_user: str = "iqtisodchi"
    postgres_password: str = ""
    postgres_db: str = "iqtisodchi"
    postgres_host: str = "db"
    postgres_port: int = 5432

    anthropic_api_key: str = ""
    ai_model: str = "claude-haiku-5-5"
    embedding_provider: str = ""  # "" yoki "voyage"
    embedding_api_key: str = ""
    embedding_model: str = "voyage-3.5-lite"
    embedding_dim: int = 1024
    rag_min_similarity: float = 0.35

    default_currency: str = "UZS"
    timezone: str = "Asia/Tashkent"

    rate_limit_per_second: int = 5
    rate_limit_ai_per_hour: int = 60
    max_message_length: int = 1000
    delete_user_messages: bool = True  # javobdan keyin foydalanuvchi xabarini o'chirish

    log_level: str = "INFO"

    @field_validator("allowed_usernames", mode="before")
    @classmethod
    def _split_usernames(cls, v):
        if isinstance(v, str):
            v = v.split(",")
        return [u.strip().lstrip("@").lower() for u in v if u.strip()]

    @field_validator("allowed_user_ids", mode="before")
    @classmethod
    def _split_ids(cls, v):
        if isinstance(v, str):
            return [int(x) for x in v.replace(" ", "").split(",") if x]
        return v

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


@lru_cache
def get_settings() -> Settings:
    return Settings()
