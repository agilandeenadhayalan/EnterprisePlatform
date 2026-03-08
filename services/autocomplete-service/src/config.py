"""
Autocomplete service configuration — loaded from environment variables.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Autocomplete service configuration."""

    # Service
    service_name: str = "autocomplete-service"
    service_port: int = 8098
    debug: bool = False

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6380

    # Kafka
    kafka_bootstrap_servers: str = "kafka:9092"

    # Autocomplete settings
    max_suggestions: int = 10

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    model_config = {"env_prefix": "", "extra": "ignore"}


settings = Settings()
