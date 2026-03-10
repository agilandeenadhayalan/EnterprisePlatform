from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "bucketing-service"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "mobility_platform"
    postgres_user: str = "mobility"
    postgres_password: str = "mobility_dev_2024"
    redis_host: str = "localhost"
    redis_port: int = 6379
    kafka_bootstrap_servers: str = "localhost:9092"
    schema_registry_url: str = "http://localhost:8081"
    clickhouse_host: str = "localhost"
    clickhouse_port: int = 8123
    clickhouse_db: str = "mobility_analytics"
    minio_endpoint: str = "localhost:9002"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    mlflow_tracking_uri: str = "http://localhost:5000"
    jwt_secret: str = "dev-secret-key"
    prometheus_url: str = "http://localhost:9090"
    grafana_url: str = "http://localhost:3000"
    jaeger_url: str = "http://localhost:16686"


settings = Settings()
