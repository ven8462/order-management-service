from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    KAFKA_BOOTSTRAP_SERVERS: str

    class Config:
        env_file = ".env"


settings = Settings()
