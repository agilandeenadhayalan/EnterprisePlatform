"""Route service configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "route-service"
    service_port: int = 8055
    debug: bool = False

    # No database needed — computation service
    kafka_bootstrap_servers: str = "kafka:9092"

    # Route calculation defaults
    average_speed_kmh: float = 30.0  # Urban average speed for ETA estimation
    road_factor: float = 1.3  # Multiplier to convert straight-line to road distance

    model_config = {"env_prefix": "", "extra": "ignore"}


settings = Settings()
