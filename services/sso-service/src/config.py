"""
SSO service configuration — loaded from environment variables.

Manages SSO provider integration (Google, GitHub, Microsoft, etc.).
Uses the same DB/Redis/JWT env vars as auth-service so all identity
services share one PostgreSQL database.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """SSO service configuration."""

    # Service
    service_name: str = "sso-service"
    service_port: int = 8015
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

    # JWT
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
