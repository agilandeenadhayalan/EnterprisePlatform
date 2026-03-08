"""
Search service configuration — loaded from environment variables.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Search service configuration."""

    # Service
    service_name: str = "search-service"
    service_port: int = 8097
    debug: bool = False

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6380

    # Kafka
    kafka_bootstrap_servers: str = "kafka:9092"

    # Search settings
    max_results: int = 50
    default_radius_km: float = 5.0

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    model_config = {"env_prefix": "", "extra": "ignore"}


settings = Settings()
