from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    AUTH_SERVICE_URL: str
    DATABASE_URL: str
    KAFKA_BOOTSTRAP_SERVERS: str
    REDIS_HOST: str
    REDIS_PORT: int
    INVENTORY_SERVICE_URL: str
    SECRET_KEY: str
    PAYMENT_SERVICE_BASE_URL: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
