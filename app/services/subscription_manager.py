"""
Subscription Manager - Handles WebSocket event subscriptions and filtering
"""

import uuid
from typing import Dict, List, Any, Set
from dataclasses import dataclass, field
from app.services.event_registry import get_event_type, EventType
from app.utils.logger import logger

logger = logger.bind(service="SubscriptionManager")


@dataclass
class Subscription:
    """User subscription to specific events with filters"""
    id: str
    conn_id: str
    event_types: List[str]
    filters: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=lambda: __import__('time').time())


class SubscriptionManager:
    """Manages event subscriptions for WebSocket connections"""
    
    def __init__(self):
        # conn_id -> List[Subscription]
        self.subscriptions: Dict[str, List[Subscription]] = {}
    
    def create_subscription(
        self,
        conn_id: str,
        event_types: List[str],
        filters: Dict[str, Any]
    ) -> str:
        """Create a new subscription"""
        sub_id = f"sub_{uuid.uuid4().hex[:8]}"
        
        subscription = Subscription(
            id=sub_id,
            conn_id=conn_id,
            event_types=event_types,
            filters=filters
        )
        
        if conn_id not in self.subscriptions:
            self.subscriptions[conn_id] = []
        
        self.subscriptions[conn_id].append(subscription)
        
        logger.info(
            "Subscription created",
            sub_id=sub_id,
            conn_id=conn_id,
            event_types=event_types,
            filters=filters
        )
        
        return sub_id
    
    def remove_subscription(self, conn_id: str, sub_id: str) -> bool:
        """Remove a specific subscription"""
        if conn_id not in self.subscriptions:
            return False
        
        subs = self.subscriptions[conn_id]
        self.subscriptions[conn_id] = [s for s in subs if s.id != sub_id]
        
        logger.info("Subscription removed", sub_id=sub_id, conn_id=conn_id)
        return True
    
    def remove_all_subscriptions(self, conn_id: str):
        """Remove all subscriptions for a connection"""
        if conn_id in self.subscriptions:
            count = len(self.subscriptions[conn_id])
            del self.subscriptions[conn_id]
            logger.info("All subscriptions removed", conn_id=conn_id, count=count)
    
    def get_subscriptions(self, conn_id: str) -> List[Subscription]:
        """Get all subscriptions for a connection"""
        return self.subscriptions.get(conn_id, [])
    
    def get_matching_connections(
        self,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> Set[str]:
        """Get connection IDs that should receive this event"""
        matching_conns = set()
        
        for conn_id, subs in self.subscriptions.items():
            for sub in subs:
                if self._matches_subscription(event_type, event_data, sub):
                    matching_conns.add(conn_id)
                    break
        
        if matching_conns:
            logger.debug("Event matched", event_type=event_type, matching_count=len(matching_conns))
        
        return matching_conns
    
    def _matches_subscription(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        subscription: Subscription
    ) -> bool:
        """Check if event matches subscription criteria"""
        # Check if event type is subscribed
        if event_type not in subscription.event_types:
            return False
        
        # Apply filters
        filters = subscription.filters
        
        # Filter: mcp_names (multiselect)
        if "mcp_names" in filters and filters["mcp_names"]:
            mcp_name = event_data.get("mcp_name")
            if mcp_name and mcp_name not in filters["mcp_names"]:
                return False
        
        # Filter: severity (multiselect)
        if "severity" in filters and filters["severity"]:
            severity = event_data.get("severity")
            if severity and severity not in filters["severity"]:
                return False
        
        # Filter: old_status (select)
        if "old_status" in filters and filters["old_status"]:
            old_status = event_data.get("old_status")
            if old_status != filters["old_status"]:
                return False
        
        # Filter: new_status (select)
        if "new_status" in filters and filters["new_status"]:
            new_status = event_data.get("new_status")
            if new_status != filters["new_status"]:
                return False
        
        # Filter: state (circuit breaker state)
        if "state" in filters and filters["state"]:
            state = event_data.get("state")
            if state and state not in filters["state"]:
                return False
        
        # Filter: health_status
        if "health_status" in filters and filters["health_status"]:
            health_status = event_data.get("health_status")
            if health_status and health_status not in filters["health_status"]:
                return False
        
        # Filter: failure_cycles (number - minimum)
        if "failure_cycles" in filters and filters["failure_cycles"]:
            failure_cycles = event_data.get("failure_cycles", 0)
            if failure_cycles < filters["failure_cycles"]:
                return False
        
        # All filters passed
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get subscription statistics"""
        total_subs = sum(len(subs) for subs in self.subscriptions.values())
        return {
            "total_connections": len(self.subscriptions),
            "total_subscriptions": total_subs,
            "avg_subs_per_conn": total_subs / len(self.subscriptions) if self.subscriptions else 0
        }
