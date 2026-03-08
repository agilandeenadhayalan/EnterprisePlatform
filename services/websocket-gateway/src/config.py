"""
WebSocket gateway configuration — loaded from environment variables.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """WebSocket gateway configuration."""

    # Service
    service_name: str = "websocket-gateway"
    service_port: int = 8096
    debug: bool = False

    # Redis (for pub/sub across gateway instances)
    redis_host: str = "localhost"
    redis_port: int = 6380

    # Kafka
    kafka_bootstrap_servers: str = "kafka:9092"

    # WebSocket settings
    ws_max_connections: int = 10000
    ws_heartbeat_interval: int = 30

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    model_config = {"env_prefix": "", "extra": "ignore"}


settings = Settings()
