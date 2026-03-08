"""
Email service configuration — loaded from environment variables.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Email service configuration."""

    # Service
    service_name: str = "email-service"
    service_port: int = 8092
    debug: bool = False

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6380

    # Kafka
    kafka_bootstrap_servers: str = "kafka:9092"

    # Email provider (stubbed)
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str = "noreply@mobility.dev"
    smtp_password: str = "dev-smtp-password"
    email_from: str = "Smart Mobility <noreply@mobility.dev>"

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    model_config = {"env_prefix": "", "extra": "ignore"}


settings = Settings()
