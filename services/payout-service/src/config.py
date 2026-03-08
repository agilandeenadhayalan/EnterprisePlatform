"""Payout service configuration."""
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    service_name: str = "payout-service"
    service_port: int = 8083
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
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    model_config = {"env_prefix": "", "extra": "ignore"}

settings = Settings()
