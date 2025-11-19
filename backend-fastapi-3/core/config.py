# core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    POSTGRE_URI: str 
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    MQTT_BROKER_HOST: str
    MQTT_BROKER_PORT: int = 1883
    MQTT_TOPIC_PREFIX: str = "cattle/sensor"
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    EMAIL_SENDER: str = "alerts@yourdomain.com"

    class Config:
        env_file = ".env"

settings = Settings()