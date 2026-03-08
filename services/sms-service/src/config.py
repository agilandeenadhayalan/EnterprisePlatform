"""
SMS service configuration — loaded from environment variables.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """SMS service configuration."""

    # Service
    service_name: str = "sms-service"
    service_port: int = 8093
    debug: bool = False

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6380

    # Kafka
    kafka_bootstrap_servers: str = "kafka:9092"

    # SMS provider (stubbed — Twilio, AWS SNS, etc.)
    sms_provider: str = "twilio"
    sms_provider_sid: str = "dev-sms-sid"
    sms_provider_token: str = "dev-sms-token"
    sms_from_number: str = "+10000000000"

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    model_config = {"env_prefix": "", "extra": "ignore"}


settings = Settings()
