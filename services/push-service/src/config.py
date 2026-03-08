"""
Push service configuration — loaded from environment variables.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Push service configuration."""

    # Service
    service_name: str = "push-service"
    service_port: int = 8091
    debug: bool = False

    # Redis (for tracking push delivery status)
    redis_host: str = "localhost"
    redis_port: int = 6380

    # Kafka
    kafka_bootstrap_servers: str = "kafka:9092"

    # Push provider (stubbed)
    push_provider: str = "firebase"
    push_provider_key: str = "dev-push-key"

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    model_config = {"env_prefix": "", "extra": "ignore"}


settings = Settings()
