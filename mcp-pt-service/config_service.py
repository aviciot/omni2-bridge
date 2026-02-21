"""Configuration Service - Load all settings from database."""

from typing import Dict, Any, Optional
import asyncpg
from logger import logger


class ConfigService:
    """Centralized configuration management from database."""
    
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
        self._cache: Dict[str, Any] = {}
    
    async def load_all(self) -> Dict[str, Any]:
        """Load all configuration from database."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT config_key, config_value FROM omni2.pt_service_config"
            )
            
            config = {}
            for row in rows:
                # Parse JSONB to dict
                value = row['config_value']
                if isinstance(value, str):
                    import json
                    value = json.loads(value)
                config[row['config_key']] = value
                self._cache[row['config_key']] = value
            
            logger.info(f"Loaded {len(config)} configuration keys from database")
            return config
    
    async def get(self, key: str, use_cache: bool = True) -> Optional[Any]:
        """Get specific configuration value."""
        if use_cache and key in self._cache:
            return self._cache[key]
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT config_value FROM omni2.pt_service_config WHERE config_key = $1",
                key
            )
            if row:
                value = row['config_value']
                if isinstance(value, str):
                    import json
                    value = json.loads(value)
                self._cache[key] = value
                return value
            return None
    
    async def update(self, key: str, value: Any, updated_by: Optional[int] = None) -> bool:
        """Update configuration value."""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE omni2.pt_service_config 
                SET config_value = $1, updated_at = NOW(), updated_by = $2
                WHERE config_key = $3
                """,
                value, updated_by, key
            )
            
            if result == "UPDATE 1":
                self._cache[key] = value
                logger.info(f"Updated config: {key}")
                return True
            return False
    
    def get_llm_config(self, provider: str) -> Optional[Dict[str, Any]]:
        """Get LLM provider configuration from cache."""
        llm_providers = self._cache.get('llm_providers', {})
        return llm_providers.get(provider)
    
    def get_execution_settings(self) -> Dict[str, Any]:
        """Get execution settings from cache."""
        return self._cache.get('execution_settings', {})
    
    def get_progress_stages(self) -> list:
        """Get progress stage definitions from cache."""
        stages_config = self._cache.get('progress_stages', {})
        return stages_config.get('stages', [])
    
    def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis configuration from cache."""
        return self._cache.get('redis_config', {})

    def get_ai_red_team_config(self) -> Dict[str, Any]:
        """Get AI Red Team configuration with safe defaults."""
        return self._cache.get('ai_red_team', {
            'enabled': True,
            'max_stories': 3,
            'max_iterations': 25,
            'attacker_provider': 'gemini',
            'attacker_model': 'gemini-2.0-flash',
            'judge_provider': 'gemini',
            'judge_model': 'gemini-2.0-flash',
        })


# Global instance
_config_service: Optional[ConfigService] = None


async def init_config_service(pool: asyncpg.Pool) -> ConfigService:
    """Initialize configuration service."""
    global _config_service
    _config_service = ConfigService(pool)
    await _config_service.load_all()
    return _config_service


def get_config_service() -> ConfigService:
    """Get configuration service instance."""
    if _config_service is None:
        raise RuntimeError("ConfigService not initialized. Call init_config_service first.")
    return _config_service
