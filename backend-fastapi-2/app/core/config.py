# app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    POSTGRE_URI:str
    MONGO_URI: str
    MONGO_DB: str
    MQTT_BROKER: str
    MQTT_PORT: int
    MQTT_TOPIC: str

    class Config:
        env_file = ".env"

settings = Settings()