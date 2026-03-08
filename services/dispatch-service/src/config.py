"""
Dispatch service configuration — loaded from environment variables.

Manages driver assignment scoring, zone management, and Kafka event production
for ride dispatch operations.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Dispatch service configuration."""

    # Service
    service_name: str = "dispatch-service"
    service_port: int = 8061
    debug: bool = False

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5433
    postgres_db: str = "mobility_platform"
    postgres_user: str = "mobility"
    postgres_password: str = "mobility_dev_2024"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6380

    # Kafka
    kafka_bootstrap_servers: str = "kafka:9092"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    model_config = {"env_prefix": "", "extra": "ignore"}


settings = Settings()
