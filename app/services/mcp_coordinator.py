"""
MCP Coordinator Service - Single Point of Control for MCP Management

This service replaces the distributed MCP management logic with a centralized
coordinator that handles health monitoring, recovery, and cache management.

Key Features:
- Single writer pattern for database updates
- Circuit breaker logic for failed MCPs
- Automatic recovery with exponential backoff
- Thread-safe cache management
- Comprehensive state transition logging
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models import MCPServer, MCPHealthLog
from app.services.circuit_breaker import get_circuit_breaker
from app.services.websocket_broadcaster import get_websocket_broadcaster
from app.utils.logger import logger
from app.database import AsyncSessionLocal

# Bind service name to logger for this module
logger = logger.bind(service="Coordinator")


class MCPCoordinator:
    """Centralized MCP management coordinator."""
    
    def __init__(self):
        self.mcps: Dict[str, any] = {}  # Active MCP connections
        self.tools_cache: Dict[str, List[Dict]] = {}  # Cached tools
        self.client_created_at: Dict[str, float] = {}  # Connection timestamps
        self.circuit_breaker = get_circuit_breaker()
        self.running = False
        self.coordinator_task: Optional[asyncio.Task] = None
        
        # State tracking
        self.last_db_scan = None
        self.recovery_queue: Set[str] = set()
        self.health_check_queue: Set[str] = set()
        
    async def start(self):
        """Start the MCP coordinator background task."""
        if self.running:
            logger.warning("🔄 MCP Coordinator already running")
            return
            
        self.running = True
        self.coordinator_task = asyncio.create_task(self._coordinator_loop())
        logger.info("🚀 MCP Coordinator started")
        
    async def stop(self):
        """Stop the MCP coordinator and cleanup resources."""
        self.running = False
        
        if self.coordinator_task:
            self.coordinator_task.cancel()
            try:
                await self.coordinator_task
            except asyncio.CancelledError:
                pass
                
        # Cleanup connections
        await self._cleanup_all_connections()
        logger.info("🛑 MCP Coordinator stopped")
        
    async def _coordinator_loop(self):
        """Main coordinator loop - runs every 30 seconds."""
        logger.info("✅ Coordinator loop starting")
        
        while self.running:
            try:
                if AsyncSessionLocal is None:
                    await asyncio.sleep(5)
                    continue
                    
                async with AsyncSessionLocal() as db:
                    # 1. Health check active MCPs
                    await self._health_check_active_mcps(db)
                    
                    # 2. Attempt recovery for failed MCPs
                    await self._attempt_recovery(db)
                    
                    # 3. Scan database for configuration changes
                    await self._scan_database_changes(db)
                    
                    # 4. Update statistics
                    await self._update_statistics(db)
                    
                await asyncio.sleep(30)  # 30 second cycle
                
            except Exception as e:
                logger.error("❌ MCP Coordinator loop error", error=str(e), exc_info=True)
                await asyncio.sleep(60)  # Longer sleep on error
                
    async def _health_check_active_mcps(self, db: AsyncSession):
        """Health check all MCPs currently in memory cache."""
        if not self.mcps:
            return
            
        logger.debug("🏥 Health checking active MCPs", count=len(self.mcps))
        
        for mcp_name in list(self.mcps.keys()):
            try:
                await self._health_check_single_mcp(db, mcp_name)
            except Exception as e:
                logger.error("❌ Health check failed", mcp=mcp_name, error=str(e))
                await self._handle_mcp_failure(db, mcp_name, str(e))
                
    async def _health_check_single_mcp(self, db: AsyncSession, mcp_name: str):
        """Perform health check on a single MCP."""
        if mcp_name not in self.mcps:
            return
            
        start_time = time.time()
        client = self.mcps[mcp_name]
        
        try:
            # Simple health check - list tools
            tools_result = await client.list_tools()
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Health check passed
            await self._handle_mcp_success(db, mcp_name, response_time_ms)
            
        except Exception as e:
            # Health check failed
            await self._handle_mcp_failure(db, mcp_name, str(e))
            
    async def _handle_mcp_success(self, db: AsyncSession, mcp_name: str, response_time_ms: int):
        """Handle successful MCP health check."""
        # Update database status
        await db.execute(
            update(MCPServer)
            .where(MCPServer.name == mcp_name)
            .values(
                health_status='healthy',
                last_health_check=datetime.now(timezone.utc),
                consecutive_failures=0
            )
        )
        
        # Log success
        await self._log_health_event(
            db, mcp_name, 'healthy', 
            response_time_ms=response_time_ms,
            event_type='health_check_success'
        )
        
        # Record success in circuit breaker
        self.circuit_breaker.record_success(mcp_name)
        
        # Broadcast status change via WebSocket
        broadcaster = get_websocket_broadcaster()
        await broadcaster.broadcast_mcp_status(
            mcp_name, 
            'healthy', 
            {'response_time_ms': response_time_ms}
        )
        
        logger.debug("✅ MCP health check passed", mcp=mcp_name, response_time=response_time_ms)
        
    async def _handle_mcp_failure(self, db: AsyncSession, mcp_name: str, error_message: str):
        """Handle MCP health check failure."""
        # Get current server info
        result = await db.execute(
            select(MCPServer).where(MCPServer.name == mcp_name)
        )
        server = result.scalar_one_or_none()
        
        if not server:
            logger.warning("⚠️ MCP not found in database", mcp=mcp_name)
            return
            
        # Increment failure count
        consecutive_failures = (server.consecutive_failures or 0) + 1
        
        # Update database status
        await db.execute(
            update(MCPServer)
            .where(MCPServer.name == mcp_name)
            .values(
                health_status='disconnected',
                last_health_check=datetime.now(timezone.utc),
                consecutive_failures=consecutive_failures
            )
        )
        
        # Remove from cache
        await self._remove_from_cache(mcp_name)
        
        # Record failure in circuit breaker
        self.circuit_breaker.record_failure(mcp_name)
        
        # Broadcast status change via WebSocket
        broadcaster = get_websocket_broadcaster()
        await broadcaster.broadcast_mcp_status(
            mcp_name, 
            'disconnected', 
            {'error': error_message, 'consecutive_failures': consecutive_failures}
        )
        
        # Check if circuit should open
        if consecutive_failures >= 5:
            await self._open_circuit(db, mcp_name)
        else:
            # Add to recovery queue
            self.recovery_queue.add(mcp_name)
            
        # Log failure
        await self._log_health_event(
            db, mcp_name, 'disconnected',
            error_message=error_message,
            event_type='health_check_failed',
            metadata={'consecutive_failures': consecutive_failures}
        )
        
        logger.warning("⚠️ MCP health check failed", 
                      mcp=mcp_name, 
                      failures=consecutive_failures, 
                      error=error_message)
                      
    async def _open_circuit(self, db: AsyncSession, mcp_name: str):
        """Open circuit breaker for failed MCP."""
        await db.execute(
            update(MCPServer)
            .where(MCPServer.name == mcp_name)
            .values(
                health_status='circuit_open',
                circuit_state='open'
            )
        )
        
        # Remove from recovery queue, add to circuit recovery
        self.recovery_queue.discard(mcp_name)
        
        await self._log_health_event(
            db, mcp_name, 'circuit_open',
            event_type='circuit_opened'
        )
        
        # Broadcast circuit breaker event via WebSocket
        broadcaster = get_websocket_broadcaster()
        await broadcaster.broadcast_health_event(
            mcp_name, 
            'circuit_opened', 
            {'threshold': 5}
        )
        
        logger.warning("⚡ Circuit breaker opened", mcp=mcp_name)
        
    async def _remove_from_cache(self, mcp_name: str):
        """Remove MCP from memory cache."""
        if mcp_name in self.mcps:
            try:
                client = self.mcps[mcp_name]
                await client.__aexit__(None, None, None)
            except Exception as e:
                logger.warning("⚠️ Error closing MCP connection", mcp=mcp_name, error=str(e))
            finally:
                del self.mcps[mcp_name]
                self.tools_cache.pop(mcp_name, None)
                self.client_created_at.pop(mcp_name, None)
                
        logger.debug("🗑️ Removed MCP from cache", mcp=mcp_name)
        
    async def _attempt_recovery(self, db: AsyncSession):
        """Attempt recovery for MCPs in recovery queue."""
        if not self.recovery_queue:
            return
            
        logger.debug("🔄 Attempting MCP recovery", count=len(self.recovery_queue))
        
        # Process recovery queue (copy to avoid modification during iteration)
        for mcp_name in list(self.recovery_queue):
            try:
                await self._attempt_single_recovery(db, mcp_name)
            except Exception as e:
                logger.error("❌ Recovery attempt failed", mcp=mcp_name, error=str(e))
                
    async def _attempt_single_recovery(self, db: AsyncSession, mcp_name: str):
        """Attempt recovery for a single MCP."""
        # Get server info
        result = await db.execute(
            select(MCPServer).where(MCPServer.name == mcp_name)
        )
        server = result.scalar_one_or_none()
        
        if not server or server.health_status not in ['disconnected', 'circuit_open']:
            self.recovery_queue.discard(mcp_name)
            return
            
        # Check circuit breaker
        if self.circuit_breaker.is_open(mcp_name):
            logger.debug("⚡ Circuit breaker open, skipping recovery", mcp=mcp_name)
            return
            
        # Attempt to load MCP
        logger.info("🔄 Attempting MCP recovery", mcp=mcp_name)
        
        # Update recovery attempt timestamp
        await db.execute(
            update(MCPServer)
            .where(MCPServer.name == mcp_name)
            .values(last_recovery_attempt=datetime.now(timezone.utc))
        )
        
        # Try to load the MCP (reuse existing load logic)
        from app.services.mcp_registry import get_mcp_registry
        registry = get_mcp_registry()
        
        try:
            await registry.load_mcp(server, db)
            
            # Recovery successful
            self.recovery_queue.discard(mcp_name)
            await self._log_health_event(
                db, mcp_name, 'healthy',
                event_type='recovery_success'
            )
            
            logger.info("✅ MCP recovery successful", mcp=mcp_name)
            
        except Exception as e:
            # Recovery failed
            await self._log_health_event(
                db, mcp_name, 'disconnected',
                error_message=str(e),
                event_type='recovery_failed'
            )
            
            logger.warning("❌ MCP recovery failed", mcp=mcp_name, error=str(e))
            
    async def _scan_database_changes(self, db: AsyncSession):
        """Scan database for MCP configuration changes."""
        # Get all active MCPs from database
        result = await db.execute(
            select(MCPServer).where(MCPServer.status == 'active')
        )
        db_mcps = result.scalars().all()
        
        current_names = set(self.mcps.keys())
        db_names = set(mcp.name for mcp in db_mcps)
        
        # Load new MCPs
        new_mcps = db_names - current_names
        if new_mcps:
            logger.info("🆕 New MCPs detected", mcps=list(new_mcps))
            for mcp in db_mcps:
                if mcp.name in new_mcps and mcp.health_status != 'disabled':
                    self.recovery_queue.add(mcp.name)
                    
        # Remove deleted MCPs
        removed_mcps = current_names - db_names
        if removed_mcps:
            logger.info("🗑️ MCPs removed", mcps=list(removed_mcps))
            for mcp_name in removed_mcps:
                await self._remove_from_cache(mcp_name)
                self.recovery_queue.discard(mcp_name)
                
    async def _update_statistics(self, db: AsyncSession):
        """Update system statistics and metrics."""
        stats = {
            'active_mcps': len(self.mcps),
            'recovery_queue': len(self.recovery_queue),
            'circuit_open_count': len([name for name in self.mcps 
                                     if self.circuit_breaker.is_open(name)])
        }
        
        logger.debug("📊 MCP Coordinator stats", **stats)
        
    async def _log_health_event(self, db: AsyncSession, mcp_name: str, status: str, 
                               response_time_ms: Optional[int] = None,
                               error_message: Optional[str] = None,
                               event_type: str = 'health_check',
                               metadata: Optional[Dict] = None):
        """Log health event to database."""
        try:
            # Get server ID
            result = await db.execute(
                select(MCPServer.id).where(MCPServer.name == mcp_name)
            )
            server_id = result.scalar_one_or_none()
            
            if server_id:
                log_entry = MCPHealthLog(
                    mcp_server_id=server_id,
                    status=status,
                    response_time_ms=response_time_ms,
                    error_message=error_message,
                    event_type=event_type,
                    metadata=metadata
                )
                db.add(log_entry)
                await db.commit()
                
        except Exception as e:
            logger.warning("⚠️ Failed to log health event", mcp=mcp_name, error=str(e))
            
    async def _cleanup_all_connections(self):
        """Cleanup all MCP connections on shutdown."""
        for mcp_name in list(self.mcps.keys()):
            await self._remove_from_cache(mcp_name)
            
    # Public interface methods
    def get_loaded_mcps(self) -> List[str]:
        """Get list of currently loaded MCP names."""
        return list(self.mcps.keys())
        
    def get_tools_cache(self) -> Dict[str, List[Dict]]:
        """Get current tools cache."""
        return self.tools_cache.copy()
        
    def is_mcp_healthy(self, mcp_name: str) -> bool:
        """Check if MCP is currently healthy and loaded."""
        return mcp_name in self.mcps


# Global coordinator instance
_coordinator: Optional[MCPCoordinator] = None


def get_mcp_coordinator() -> MCPCoordinator:
    """Get global MCP coordinator instance."""
    global _coordinator
    if _coordinator is None:
        _coordinator = MCPCoordinator()
    return _coordinator


async def start_mcp_coordinator():
    """Start the global MCP coordinator."""
    coordinator = get_mcp_coordinator()
    await coordinator.start()
    
    
async def stop_mcp_coordinator():
    """Stop the global MCP coordinator."""
    coordinator = get_mcp_coordinator()
    await coordinator.stop()