"""
Kafka Consumer Rides — configuration loaded from environment variables.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Kafka consumer rides configuration."""

    service_name: str = "kafka-consumer-rides"
    service_port: int = 8113
    debug: bool = False

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "mobility_platform"
    postgres_user: str = "mobility"
    postgres_password: str = "mobility_dev_2024"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379

    # Kafka
    kafka_bootstrap_servers: str = "localhost:29094"

    # ClickHouse
    clickhouse_host: str = "localhost"
    clickhouse_port: int = 8123
    clickhouse_db: str = "mobility_analytics"
    clickhouse_user: str = "default"
    clickhouse_password: str = ""

    # MinIO
    minio_endpoint: str = "localhost:9002"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"

    # Archive settings
    archive_bucket: str = "bronze"
    archive_prefix: str = "kafka/ride.events.v1"
    buffer_size: int = 50

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    model_config = {"env_prefix": "", "extra": "ignore"}


settings = Settings()
