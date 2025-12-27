"""
User Service

Handles user lookup, permissions, and MCP access control.
"""

from typing import Dict, List, Optional, Any, Union
from app.config import settings
from app.utils.logger import logger


class UserService:
    """Service for managing user permissions and MCP access."""
    
    def __init__(self):
        """Initialize user service with config."""
        self.default_user = settings.users_config.get("default_user", {})
        self.super_admins = settings.users_config.get("super_admins", [])
        self.users = {user["email"]: user for user in settings.users_config.get("users", [])}
        
    def get_user(self, user_id: str) -> Dict[str, Any]:
        """
        Get user configuration by ID (email).
        
        Args:
            user_id: User email address
            
        Returns:
            User config dict
        """
        # Check super admins first
        for admin in self.super_admins:
            if admin["email"] == user_id:
                return admin
        
        # Check regular users
        if user_id in self.users:
            return self.users[user_id]
        
        # Return default user for unknown users
        logger.warning(
            "Unknown user, using default configuration",
            user_id=user_id,
            default_role=self.default_user["role"],
        )
        return {
            **self.default_user,
            "email": user_id,
            "name": "Guest User",
        }
    
    def get_allowed_mcps(self, user_id: str) -> Union[str, List[str]]:
        """
        Get list of MCPs user can access.
        
        Args:
            user_id: User email address
            
        Returns:
            List of MCP names or "*" for all
        """
        user = self.get_user(user_id)
        allowed = user.get("allowed_mcps", [])
        
        if allowed == "*":
            return "*"
        
        return allowed if isinstance(allowed, list) else []
    
    def can_access_mcp(self, user_id: str, mcp_name: str) -> bool:
        """
        Check if user can access specific MCP.
        
        Args:
            user_id: User email address
            mcp_name: Name of MCP server
            
        Returns:
            True if user has access
        """
        allowed_mcps = self.get_allowed_mcps(user_id)
        
        if allowed_mcps == "*":
            return True
        
        return mcp_name in allowed_mcps
    
    def get_allowed_domains(self, user_id: str) -> Union[str, List[str]]:
        """
        Get list of knowledge domains user can query.
        
        Args:
            user_id: User email address
            
        Returns:
            List of domain names or "*" for all
        """
        user = self.get_user(user_id)
        allowed = user.get("allowed_domains", [])
        
        if allowed == "*":
            return "*"
        
        return allowed if isinstance(allowed, list) else []
    
    def can_ask_domain(self, user_id: str, domain: str) -> bool:
        """
        Check if user can ask questions in specific domain.
        
        Args:
            user_id: User email address
            domain: Domain name (e.g., "python_help")
            
        Returns:
            True if user has access
        """
        allowed_domains = self.get_allowed_domains(user_id)
        
        if allowed_domains == "*":
            return True
        
        return domain in allowed_domains


# Global user service instance
_user_service: Optional[UserService] = None


def get_user_service() -> UserService:
    """
    Get or create the global user service instance.
    
    Returns:
        UserService instance
    """
    global _user_service
    if _user_service is None:
        _user_service = UserService()
    return _user_service
