"""
Config service configuration — loaded from environment variables.

WHY pydantic-settings? It provides type-safe config with automatic env var
loading, validation, and default values. No more os.getenv() scattered
throughout the codebase with string-to-int conversions.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Config service configuration."""

    # Service
    service_name: str = "config-service"
    service_port: int = 8030
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

    # JWT (needed for token verification via middleware)
    jwt_secret_key: str = "dev-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"

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
