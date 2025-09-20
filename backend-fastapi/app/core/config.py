from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Backend Capstone D06"
    VERSION: str = "1.0.0"
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 5000
    DEBUG: bool = False

    # MongoDB
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB: str = "fastapi_db"

    class Config:
        env_file = ".env"

settings = Settings()
