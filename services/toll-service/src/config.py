"""Toll service configuration."""
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    service_name: str = "toll-service"
    service_port: int = 8086
    debug: bool = False
    kafka_bootstrap_servers: str = "kafka:9092"

    model_config = {"env_prefix": "", "extra": "ignore"}

settings = Settings()
