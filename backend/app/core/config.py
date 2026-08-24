from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    google_client_id: str
    google_client_secret: str

    jwt_secret: str

    gemini_api_key: str
    groq_api_key: str = ""

    default_gemini_model: str = "gemini-2.5-flash"

    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    database_url: str
    redis_url: str

    app_timezone: str = "Asia/Karachi"

    mcp_enabled: bool = True
    mcp_server_url: str = ""
    mcp_timeout_seconds: float = 12.0

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
