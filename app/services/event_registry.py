"""
Event Registry - Centralized event type definitions

This module defines all available event types, their categories, and metadata.
Adding new events is as simple as adding entries to the registry.
"""

from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum


class EventCategory(str, Enum):
    """Event categories for organization"""
    MCP = "mcp"
    USER = "user"
    SYSTEM = "system"
    AUDIT = "audit"


@dataclass
class EventField:
    """Filterable field definition"""
    name: str
    label: str
    type: str  # "select", "multiselect", "text", "number"
    options: List[str] = None  # For select/multiselect
    dynamic: bool = False  # If options are loaded dynamically


@dataclass
class EventType:
    """Event type definition"""
    id: str
    category: EventCategory
    label: str
    description: str
    icon: str
    severity_levels: List[str]
    filterable_fields: List[EventField]


# ============================================================================
# EVENT REGISTRY - Add new events here
# ============================================================================

EVENT_REGISTRY: Dict[str, EventType] = {
    # ========================================================================
    # MCP EVENTS
    # ========================================================================
    "mcp_status_change": EventType(
        id="mcp_status_change",
        category=EventCategory.MCP,
        label="MCP Status Change",
        description="MCP server status changed (active/inactive)",
        icon="🔄",
        severity_levels=["info", "warning", "error"],
        filterable_fields=[
            EventField(
                name="mcp_names",
                label="MCP Servers",
                type="multiselect",
                dynamic=True  # Load from database
            ),
            EventField(
                name="old_status",
                label="From Status",
                type="select",
                options=["active", "inactive", "circuit_open"]
            ),
            EventField(
                name="new_status",
                label="To Status",
                type="select",
                options=["active", "inactive", "circuit_open"]
            ),
            EventField(
                name="severity",
                label="Severity",
                type="multiselect",
                options=["info", "warning", "error"]
            )
        ]
    ),
    
    "circuit_breaker_state": EventType(
        id="circuit_breaker_state",
        category=EventCategory.MCP,
        label="Circuit Breaker State",
        description="Circuit breaker state transition",
        icon="⚡",
        severity_levels=["info", "warning", "error"],
        filterable_fields=[
            EventField(
                name="mcp_names",
                label="MCP Servers",
                type="multiselect",
                dynamic=True
            ),
            EventField(
                name="state",
                label="Circuit State",
                type="multiselect",
                options=["CLOSED", "OPEN", "HALF_OPEN"]
            ),
            EventField(
                name="severity",
                label="Severity",
                type="multiselect",
                options=["info", "warning", "error"]
            )
        ]
    ),
    
    "mcp_health_check": EventType(
        id="mcp_health_check",
        category=EventCategory.MCP,
        label="Health Check",
        description="MCP health check result",
        icon="🏥",
        severity_levels=["info", "warning", "error"],
        filterable_fields=[
            EventField(
                name="mcp_names",
                label="MCP Servers",
                type="multiselect",
                dynamic=True
            ),
            EventField(
                name="health_status",
                label="Health Status",
                type="multiselect",
                options=["healthy", "unhealthy", "degraded"]
            ),
            EventField(
                name="severity",
                label="Severity",
                type="multiselect",
                options=["info", "warning", "error"]
            )
        ]
    ),
    
    "mcp_auto_disabled": EventType(
        id="mcp_auto_disabled",
        category=EventCategory.MCP,
        label="Auto-Disabled",
        description="MCP automatically disabled after failures",
        icon="🚫",
        severity_levels=["error", "critical"],
        filterable_fields=[
            EventField(
                name="mcp_names",
                label="MCP Servers",
                type="multiselect",
                dynamic=True
            ),
            EventField(
                name="failure_cycles",
                label="Min Failure Cycles",
                type="number"
            )
        ]
    ),
    
    # ========================================================================
    # USER EVENTS (Placeholder for future)
    # ========================================================================
    "user_login": EventType(
        id="user_login",
        category=EventCategory.USER,
        label="User Login",
        description="User logged in",
        icon="🔐",
        severity_levels=["info"],
        filterable_fields=[
            EventField(
                name="user_roles",
                label="User Roles",
                type="multiselect",
                options=["admin", "developer", "dba", "viewer"]
            )
        ]
    ),
    
    "user_action": EventType(
        id="user_action",
        category=EventCategory.USER,
        label="User Action",
        description="User performed an action",
        icon="👤",
        severity_levels=["info", "warning"],
        filterable_fields=[
            EventField(
                name="action_type",
                label="Action Type",
                type="multiselect",
                options=["enable_mcp", "disable_mcp", "reload_mcp", "delete_mcp"]
            ),
            EventField(
                name="user_roles",
                label="User Roles",
                type="multiselect",
                options=["admin", "developer", "dba", "viewer"]
            )
        ]
    ),
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_events_by_category(category: EventCategory) -> List[EventType]:
    """Get all events for a category"""
    return [event for event in EVENT_REGISTRY.values() if event.category == category]


def get_event_type(event_id: str) -> EventType:
    """Get event type by ID"""
    return EVENT_REGISTRY.get(event_id)


def get_all_categories() -> List[EventCategory]:
    """Get all available categories"""
    return list(EventCategory)


def get_event_metadata() -> Dict[str, Any]:
    """Get metadata for frontend (event types, fields, options)"""
    return {
        "categories": [
            {
                "id": cat.value,
                "label": cat.value.upper(),
                "events": [
                    {
                        "id": event.id,
                        "label": event.label,
                        "description": event.description,
                        "icon": event.icon,
                        "severity_levels": event.severity_levels,
                        "fields": [
                            {
                                "name": field.name,
                                "label": field.label,
                                "type": field.type,
                                "options": field.options,
                                "dynamic": field.dynamic
                            }
                            for field in event.filterable_fields
                        ]
                    }
                    for event in get_events_by_category(cat)
                ]
            }
            for cat in EventCategory
        ]
    }
