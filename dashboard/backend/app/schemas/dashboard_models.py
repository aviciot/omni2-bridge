"""
Dashboard Schema Models
=======================
Pydantic models for omni2_dashboard schema.
MUST stay in sync with init_dashboard.py!

User data comes from auth_service via API, not stored here.
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal


# ============================================================================
# DASHBOARD CONFIG
# ============================================================================

class DashboardConfigBase(BaseModel):
    key: str
    value: Optional[str] = None
    description: Optional[str] = None


class DashboardConfigCreate(DashboardConfigBase):
    pass


class DashboardConfigUpdate(BaseModel):
    value: Optional[str] = None
    description: Optional[str] = None


class DashboardConfig(DashboardConfigBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# USER PREFERENCES
# ============================================================================

class UserPreferencesBase(BaseModel):
    user_id: int  # References auth_service.users.id (no FK)
    theme: str = "dark"
    layout: Dict[str, Any] = {}
    favorite_mcps: List[str] = []
    hidden_widgets: List[str] = []


class UserPreferencesCreate(UserPreferencesBase):
    pass


class UserPreferencesUpdate(BaseModel):
    theme: Optional[str] = None
    layout: Optional[Dict[str, Any]] = None
    favorite_mcps: Optional[List[str]] = None
    hidden_widgets: Optional[List[str]] = None


class UserPreferences(UserPreferencesBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# DASHBOARD CACHE
# ============================================================================

class DashboardCacheBase(BaseModel):
    cache_key: str
    cache_value: Dict[str, Any]
    expires_at: datetime


class DashboardCacheCreate(DashboardCacheBase):
    pass


class DashboardCache(DashboardCacheBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# ACTIVITY FEED
# ============================================================================

class ActivityFeedBase(BaseModel):
    user_id: int  # References auth_service.users.id (no FK)
    username: str  # Denormalized for display
    action: str
    resource: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ActivityFeedCreate(ActivityFeedBase):
    pass


class ActivityFeed(ActivityFeedBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# MCP USAGE STATS
# ============================================================================

class MCPUsageStatsBase(BaseModel):
    mcp_name: str
    tool_name: Optional[str] = None
    user_id: Optional[int] = None  # References auth_service.users.id (no FK)
    success: bool
    duration_ms: Optional[int] = None
    cost: Optional[Decimal] = None


class MCPUsageStatsCreate(MCPUsageStatsBase):
    pass


class MCPUsageStats(MCPUsageStatsBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True


# ============================================================================
# AGGREGATED STATS (Computed, not stored)
# ============================================================================

class DashboardStats(BaseModel):
    """Hero stats for dashboard"""
    total_queries: int
    active_users: int
    success_rate: float
    avg_response_time: int
    total_cost: Decimal


class MCPStats(BaseModel):
    """Per-MCP statistics"""
    mcp_name: str
    total_calls: int
    success_rate: float
    avg_duration_ms: int
    total_cost: Decimal


class UserActivity(BaseModel):
    """User activity summary"""
    user_id: int
    username: str
    total_queries: int
    last_active: datetime
    favorite_mcp: Optional[str] = None
