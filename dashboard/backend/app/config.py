from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    OMNI2_WS_URL: str = "ws://host.docker.internal:8090/ws"  # WebSocket URL (via Traefik)
    OMNI2_HTTP_URL: str = "http://host.docker.internal:8090"  # HTTP API URL (via Traefik)
    OMNI2_DIRECT_URL: str = "http://omni2:8000"  # Direct to OMNI2 (bypass Traefik for internal calls)
    ENVIRONMENT: str = "development"
    DEV_MODE: bool = False
    CORS_ORIGINS: str = "http://localhost:3001,http://localhost:8090"
    LOG_LEVEL: str = "INFO"
    MCP_TIMEOUT_SECONDS: int = 120
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)
    
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

settings = Settings()
