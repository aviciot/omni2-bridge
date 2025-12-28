"""
Chat Router

LLM-powered chat interface for intelligent MCP routing.
"""

import time
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field

from app.services.llm_service import get_llm_service, LLMService
from app.services.audit_service import get_audit_service, AuditService
from app.utils.logger import logger


router = APIRouter(prefix="/chat")


# ============================================================
# Request/Response Models
# ============================================================

class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    
    user_id: str = Field(..., description="User email address")
    message: str = Field(..., description="User's question or request")
    slack_context: Optional[dict] = Field(None, description="Slack metadata (user_id, channel, message_ts, thread_ts, event_type)")


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    
    success: bool
    answer: str
    tool_calls: int = 0
    tools_used: list = []
    iterations: int = 1
    error: Optional[str] = None
    warning: Optional[str] = None


# ============================================================
# Endpoints
# ============================================================

@router.post("/ask", response_model=ChatResponse)
async def ask_question(
    request: ChatRequest,
    http_request: Request,
    llm_service: LLMService = Depends(get_llm_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> ChatResponse:
    """
    Ask a question with intelligent MCP routing.
    
    The LLM will:
    1. Determine if question needs MCP tools
    2. Call appropriate tools based on user permissions
    3. Synthesize a natural language answer
    
    Args:
        request: Chat request with user_id and message
        http_request: FastAPI request object (for IP, user agent)
        llm_service: LLM service instance (injected)
        audit_service: Audit service instance (injected)
        
    Returns:
        ChatResponse with answer and metadata
        
    Examples:
        ```json
        {
          "user_id": "developer@company.com",
          "message": "Show my Python repos"
        }
        ```
        
        ```json
        {
          "user_id": "dba@company.com",
          "message": "What's the database health?"
        }
        ```
    """
    start_time = time.time()
    
    try:
        logger.info(
            "📬 Chat request received",
            user=request.user_id,
            message_preview=request.message[:50],
        )
        
        # Process with LLM
        result = await llm_service.ask(
            user_id=request.user_id,
            message=request.message,
        )
        
        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Extract Slack context if provided
        slack_user_id = None
        slack_channel = None
        slack_message_ts = None
        slack_thread_ts = None
        
        if request.slack_context:
            slack_user_id = request.slack_context.get("slack_user_id")
            slack_channel = request.slack_context.get("slack_channel")
            slack_message_ts = request.slack_context.get("slack_message_ts")
            slack_thread_ts = request.slack_context.get("slack_thread_ts")
        
        # Determine source from headers
        source = http_request.headers.get("x-source", "web")  # "slack-bot" or "web"
        
        # Log to audit (async, non-blocking)
        await audit_service.log_chat_request(
            user_id=request.user_id,
            message=request.message,
            result=result,
            duration_ms=duration_ms,
            ip_address=http_request.client.host if http_request.client else None,
            user_agent=http_request.headers.get("user-agent"),
            slack_user_id=slack_user_id,
            slack_channel=slack_channel,
            slack_message_ts=slack_message_ts,
            slack_thread_ts=slack_thread_ts,
        )
        
        return ChatResponse(
            success=True,
            answer=result["answer"],
            tool_calls=result.get("tool_calls", 0),
            tools_used=result.get("tools_used", []),
            iterations=result.get("iterations", 1),
            warning=result.get("warning"),
        )
        
    except ValueError as e:
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Log error to audit
        await audit_service.log_error(
            user_id=request.user_id,
            message=request.message,
            error_message=str(e),
            duration_ms=duration_ms,
            ip_address=http_request.client.host if http_request.client else None,
            user_agent=http_request.headers.get("user-agent"),
        )
        
        logger.warning("⚠️  Invalid chat request", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Log error to audit
        await audit_service.log_error(
            user_id=request.user_id,
            message=request.message,
            error_message=str(e),
            duration_ms=duration_ms,
            ip_address=http_request.client.host if http_request.client else None,
            user_agent=http_request.headers.get("user-agent"),
        )
        
        logger.error(
            "❌ Chat request failed",
            user=request.user_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Chat request failed: {str(e)}",
        )
