from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    GateKeeper System Configuration.
    Loads environment variables automatically from .env or system environment.
    """
    APP_NAME: str = "GateKeeper"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000

    # Default upstream backend URL to proxy requests to
    # Example: If your main backend is running on port 9000
    UPSTREAM_URL: str = "https://httpbin.org"

    # Redis Configuration (Used for Caching & Rate Limiting)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Rate Limiting Defaults: 60 requests per 60 seconds (1 minute)
    RATE_LIMIT_REQUESTS: int = 60
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # Cache TTL Defaults (in seconds)
    CACHE_TTL_SECONDS: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings()
