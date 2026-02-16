from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    postgres_auth_url: str = (
        "postgresql://postgres:password123@postgres_auth:5432/authdb"
    )
    secret_key: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    model_config = {"env_file": "../../.env"}


settings = Settings()
