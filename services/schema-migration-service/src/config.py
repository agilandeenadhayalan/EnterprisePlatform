"""
Schema Migration service configuration — loaded from environment variables.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Schema Migration service configuration."""

    service_name: str = "Schema Migration Service"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "mobility_platform"
    postgres_user: str = "mobility"
    postgres_password: str = "mobility_dev_2024"
    redis_host: str = "localhost"
    redis_port: int = 6379
    kafka_bootstrap_servers: str = "localhost:29094"
    clickhouse_host: str = "localhost"
    clickhouse_port: int = 8123
    clickhouse_db: str = "mobility_analytics"
    clickhouse_user: str = "default"
    clickhouse_password: str = ""
    minio_endpoint: str = "localhost:9002"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"


settings = Settings()
