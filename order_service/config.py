from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str
    KAFKA_BOOTSTRAP_SERVERS: str
    REDIS_HOST: str
    REDIS_PORT: int
    INVENTORY_SERVICE_URL: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
