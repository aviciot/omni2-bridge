from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    # CRITICAL: Single source of truth for all Traefik communication
    # ALL services MUST use this parameter - NEVER hardcode URLs!
    TRAEFIK_BASE_URL: str = "http://host.docker.internal:8090"
    ENVIRONMENT: str = "development"
    DEV_MODE: bool = False
    CORS_ORIGINS: str = "http://localhost:3001,http://localhost:8090"
    LOG_LEVEL: str = "INFO"
    MCP_TIMEOUT_SECONDS: int = 120
    
    # Redis
    REDIS_HOST: str = "omni2-redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)
    
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"
    
    @property
    def omni2_api_url(self) -> str:
        """Get OMNI2 API URL (always via Traefik)"""
        return f"{self.TRAEFIK_BASE_URL}/api/v1"
    
    @property
    def omni2_ws_url(self) -> str:
        """Get OMNI2 WebSocket URL (always via Traefik)"""
        return self.TRAEFIK_BASE_URL.replace("http://", "ws://") + "/ws"
    
    @property
    def auth_service_url(self) -> str:
        """Get Auth Service URL (always via Traefik)"""
        return f"{self.TRAEFIK_BASE_URL}/auth/api/v1"

settings = Settings()
