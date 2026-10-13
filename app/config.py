from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "GateKeeper-Proxy"
    ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000

    # Upstream service to proxy requests to (default to httpbin.org for testing/demo)
    UPSTREAM_URL: str = "https://httpbin.org"

    # Redis connection URL
    REDIS_URL: str = "redis://localhost:6379/0"

    # Proxy timeout in seconds
    PROXY_TIMEOUT_SECONDS: float = 30.0

    # Rate limiting configuration (per client / API key)
    RATE_LIMIT_REQUESTS: int = 60
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
