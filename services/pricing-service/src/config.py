"""
Pricing service configuration — loaded from environment variables.

Manages fare rules and rate tables for different vehicle types.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Pricing service configuration."""

    service_name: str = "pricing-service"
    service_port: int = 8070
    debug: bool = False

    postgres_host: str = "localhost"
    postgres_port: int = 5433
    postgres_db: str = "mobility_platform"
    postgres_user: str = "mobility"
    postgres_password: str = "mobility_dev_2024"

    redis_host: str = "localhost"
    redis_port: int = 6380

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
