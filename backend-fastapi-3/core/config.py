# core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # URL koneksi async: "postgresql+asyncpg://user:pass@host/db"
    POSTGRE_URI: str 
    # JWT_SECRET_KEY: str
    # JWT_ALGORITHM: str = "HS256"
    # ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    class Config:
        env_file = ".env"

settings = Settings()