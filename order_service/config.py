from pydantic import BaseSettings

class Settings(BaseSettings):
    # This tells Pydantic to find and load a variable named DATABASE_URL
    DATABASE_URL: str
    
    # This tells Pydantic to find and load a variable named KAFKA_BOOTSTRAP_SERVERS
    KAFKA_BOOTSTRAP_SERVERS: str

    class Config:
        # This specifies the source file for these variables
        env_file = ".env"

# This creates a single, validated settings object that the rest of the app can use
settings = Settings()