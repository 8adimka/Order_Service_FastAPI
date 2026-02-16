from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    postgres_orders_url: str = (
        "postgresql://postgres:password123@postgres_orders:5432/ordersdb"
    )
    secret_key: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    algorithm: str = "HS256"
    kafka_bootstrap_servers: str = "kafka:29092"
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/0"

    model_config = {"env_file": "../../.env"}


settings = Settings()
