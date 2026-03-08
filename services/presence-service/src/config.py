"""
Presence service configuration — loaded from environment variables.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Presence service configuration."""

    # Service
    service_name: str = "presence-service"
    service_port: int = 8095
    debug: bool = False

    # Redis (primary store for presence data)
    redis_host: str = "localhost"
    redis_port: int = 6380

    # Kafka
    kafka_bootstrap_servers: str = "kafka:9092"

    # Presence settings
    heartbeat_ttl_seconds: int = 60

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    model_config = {"env_prefix": "", "extra": "ignore"}


settings = Settings()
