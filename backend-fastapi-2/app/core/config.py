# app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    POSTGRE_URI:str

    class Config:
        env_file = ".env"

settings = Settings()