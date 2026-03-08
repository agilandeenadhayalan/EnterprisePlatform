"""
Driver matching service configuration — loaded from environment variables.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Driver matching service configuration."""

    # Service
    service_name: str = "driver-matching-service"
    service_port: int = 8043
    debug: bool = False

    # Kafka
    kafka_bootstrap_servers: str = "kafka:9092"

    # Matching weights
    distance_weight: float = 0.5
    rating_weight: float = 0.3
    acceptance_rate_weight: float = 0.2
    max_distance_km: float = 10.0

    model_config = {"env_prefix": "", "extra": "ignore"}


settings = Settings()
