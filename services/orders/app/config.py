import os
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    postgres_orders_host: str = "postgres_orders"
    postgres_orders_port: int = 5432
    postgres_orders_db: str = "ordersdb"
    postgres_orders_user: str = "postgres"
    postgres_orders_password: str = "orders_password_change_in_prod_456"

    algorithm: str = "RS256"
    kafka_bootstrap_servers: str = "kafka:29092"
    redis_url: str = "redis://redis:6379/0"
    redis_limiter_url: str = "redis://redis:6379/2"  # Отдельная БД для rate limiter
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"

    # Путь к публичному ключу для проверки JWT токенов
    public_key_path: str = "/app/keys/public.pem"

    @property
    def postgres_orders_url(self) -> str:
        # Используем переменные окружения или значения по умолчанию
        user = os.getenv("POSTGRES_USER", self.postgres_orders_user)
        password = os.getenv("POSTGRES_ORDERS_PASSWORD", self.postgres_orders_password)
        host = os.getenv("POSTGRES_ORDERS_HOST", self.postgres_orders_host)
        port = os.getenv("POSTGRES_ORDERS_PORT", str(self.postgres_orders_port))
        db = os.getenv("POSTGRES_ORDERS_DB", self.postgres_orders_db)
        return f"postgresql://{user}:{password}@{host}:{port}/{db}"

    @property
    def public_key(self) -> str:
        # Читаем публичный ключ из файла
        key_path = Path(self.public_key_path)
        if not key_path.exists():
            # Для разработки: если файла нет, используем ключ из переменной окружения
            public_key_env = os.getenv("ORDERS_PUBLIC_KEY")
            if public_key_env:
                return public_key_env
            # Генерируем тестовый ключ для разработки
            return self._generate_fallback_public_key()
        return key_path.read_text()

    def _generate_fallback_public_key(self) -> str:
        """Генерирует тестовый публичный ключ для разработки"""
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        public_key = private_key.public_key()
        return public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")

    model_config = {"env_file": "../../.env", "env_prefix": "ORDERS_"}


settings = Settings()
