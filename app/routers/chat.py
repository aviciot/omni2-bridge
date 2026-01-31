"""
Chat Router

LLM-powered chat interface for intelligent MCP routing.
"""

import time
import json
import math
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.llm_service import get_llm_service, LLMService
from app.services.audit_service import get_audit_service, AuditService
from app.services.user_service import get_user_service, UserService
from app.services.rate_limiter import get_rate_limiter, RateLimiter
from app.services.usage_limit_service import get_usage_limit_service, UsageLimitService
from app.services.chat_context_service import get_chat_context_service, ChatContextService
from app.utils.logger import logger


router = APIRouter(prefix="/api/v1/chat")


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


def _format_usage_limit_error(limit_status: dict) -> str:
    exceeded = []
    if limit_status.get("exceeded_requests"):
        exceeded.append("requests")
    if limit_status.get("exceeded_tokens"):
        exceeded.append("tokens")
    if limit_status.get("exceeded_cost"):
        exceeded.append("cost")

    exceeded_label = ", ".join(exceeded) if exceeded else "usage"
    message = f"Usage limit exceeded ({exceeded_label})."

    reset_at = limit_status.get("window_end")
    if isinstance(reset_at, datetime):
        delta = reset_at - datetime.utcnow()
        reset_in_days = max(0, math.ceil(delta.total_seconds() / 86400)) if delta.total_seconds() > 0 else 0
        if reset_in_days == 0:
            message += f" Window resets at {reset_at.isoformat()} UTC."
        elif reset_in_days == 1:
            message += f" Window resets in 1 day at {reset_at.isoformat()} UTC."
        else:
            message += f" Window resets in {reset_in_days} days at {reset_at.isoformat()} UTC."
    return message


# ============================================================
# Endpoints
# ============================================================

@router.post("/ask", response_model=ChatResponse)
async def ask_question(
    request: ChatRequest,
    http_request: Request,
    llm_service: LLMService = Depends(get_llm_service),
    audit_service: AuditService = Depends(get_audit_service),
    user_service: UserService = Depends(get_user_service),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
    usage_limit_service: UsageLimitService = Depends(get_usage_limit_service),
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
        
        # Get user info for rate limiting
        user_info = await user_service.get_user(request.user_id)
        user_role = user_info.get("role", "default")
        
        # Check rate limit
        allowed, current_count, limit = rate_limiter.check_rate_limit(
            user_id=request.user_id,
            role=user_role
        )
        
        if not allowed:
            # Get reset time
            reset_time = rate_limiter.get_window_reset_time(request.user_id)
            reset_in_seconds = int(reset_time - time.time()) if reset_time else 3600
            reset_in_minutes = reset_in_seconds // 60
            
            error_msg = (
                f"Rate limit exceeded. You've made {current_count}/{limit} requests in the last hour. "
                f"Please try again in {reset_in_minutes} minutes."
            )
            
            logger.warning(
                "🚫 Rate limit exceeded",
                user=request.user_id,
                role=user_role,
                count=current_count,
                limit=limit,
                reset_in_minutes=reset_in_minutes
            )
            
            # Log rate limit violation to audit
            await audit_service.log_error(
                user_id=request.user_id,
                message=request.message,
                error_message=f"Rate limit exceeded: {current_count}/{limit} requests",
                duration_ms=0,
                ip_address=http_request.client.host if http_request.client else None,
                user_agent=http_request.headers.get("user-agent"),
            )
            
            raise HTTPException(
                status_code=429,
                detail=error_msg
            )

        limit_status = await usage_limit_service.check_user_limit(request.user_id)
        if not limit_status.get("allowed", True):
            error_msg = _format_usage_limit_error(limit_status)
            await audit_service.log_error(
                user_id=request.user_id,
                message=request.message,
                error_message=error_msg,
                duration_ms=0,
                ip_address=http_request.client.host if http_request.client else None,
                user_agent=http_request.headers.get("user-agent"),
            )
            raise HTTPException(status_code=429, detail=error_msg)

        logger.debug(
            "✅ Rate limit check passed",
            user=request.user_id,
            role=user_role,
            count=current_count,
            limit=limit
        )
        
        # Check if request is from admin dashboard
        is_admin_dashboard = http_request.headers.get("x-source") == "omni2-admin-dashboard"
        
        # Process with LLM
        result = await llm_service.ask(
            user_id=request.user_id,
            message=request.message,
            is_admin_dashboard=is_admin_dashboard,
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


@router.post("/ask/stream")
async def ask_question_stream(
    request: ChatRequest,
    http_request: Request,
    llm_service: LLMService = Depends(get_llm_service),
    context_service: ChatContextService = Depends(get_chat_context_service),
):
    """
    Stream chat response with Phase 1 authorization checks.
    """
    start_time = time.time()
    
    # Extract user_id from Traefik header (INTEGER)
    user_id_header = http_request.headers.get("X-User-Id")
    logger.info(f"[PHASE1] Received request - X-User-Id header: {user_id_header}")
    
    if not user_id_header:
        async def error_stream():
            yield f"event: error\ndata: {json.dumps({'error': 'Missing X-User-Id header'})}\n\n"
        return StreamingResponse(error_stream(), media_type="text/event-stream")
    
    try:
        user_id = int(user_id_header)
        logger.info(f"[PHASE1] Parsed user_id: {user_id}")
    except ValueError:
        async def error_stream():
            yield f"event: error\ndata: {json.dumps({'error': 'Invalid X-User-Id header'})}\n\n"
        return StreamingResponse(error_stream(), media_type="text/event-stream")
    
    # Load user context
    try:
        context = await context_service.load_user_context(user_id)
        logger.info(f"[PHASE1] Loaded context - email: {context['email']}, username: {context['username']}, role: {context['role_name']}")
    except Exception as e:
        logger.error(f"[PHASE1] Failed to load context: {str(e)}")
        async def error_stream():
            yield f"event: error\ndata: {json.dumps({'error': f'Failed to load user context: {str(e)}'})}\n\n"
        return StreamingResponse(error_stream(), media_type="text/event-stream")
    
    # Check if user is blocked
    is_blocked, block_reason = await context_service.check_user_blocked(user_id)
    logger.info(f"[PHASE1] Block check - is_blocked: {is_blocked}, reason: {block_reason}")
    if is_blocked:
        logger.warning(f"[PHASE1] User {user_id} is blocked: {block_reason}")
        block_msg = f"🚫 Access Blocked\n\n{block_reason or 'Contact administrator for more information.'}"
        async def blocked_stream():
            # Send block message as tokens (same as welcome)
            for char in block_msg:
                payload = json.dumps({"text": char})
                yield f"event: token\ndata: {payload}\n\n"
            # Send done event
            yield f"event: done\ndata: {{}}\n\n"
        return StreamingResponse(blocked_stream(), media_type="text/event-stream")
    
    # Check if user account is active
    if not context['active']:
        inactive_msg = "🚫 Account Inactive\n\nYour account has been deactivated. Please contact your administrator."
        async def inactive_stream():
            for char in inactive_msg:
                payload = json.dumps({"text": char})
                yield f"event: token\ndata: {payload}\n\n"
            yield f"event: done\ndata: {{}}\n\n"
        return StreamingResponse(inactive_stream(), media_type="text/event-stream")
    
    # Check usage limits
    usage = await context_service.check_usage_limit(user_id, context['cost_limit_daily'])
    logger.info(f"[PHASE1] Usage check - allowed: {usage['allowed']}, used: ${usage['cost_used']:.2f}, limit: ${usage['cost_limit']:.2f}")
    if not usage['allowed']:
        limit_msg = f"🚨 Daily Limit Exceeded\n\nYou've used ${usage['cost_used']:.2f} of your ${usage['cost_limit']:.2f} daily limit.\nYour limit will reset tomorrow."
        async def limit_stream():
            for char in limit_msg:
                payload = json.dumps({"text": char})
                yield f"event: token\ndata: {payload}\n\n"
            yield f"event: done\ndata: {{}}\n\n"
        return StreamingResponse(limit_stream(), media_type="text/event-stream")
    
    # Get welcome message
    welcome = await context_service.get_welcome_message(user_id, context['role_id'])
    logger.info(f"[PHASE1] Welcome message loaded: {welcome['message'][:50]}...")
    
    # Get available MCPs
    available_mcps = await context_service.get_available_mcps(context['mcp_access'])
    logger.info(f"[PHASE1] Available MCPs: {[mcp['name'] for mcp in available_mcps]}")
    logger.info(f"[PHASE1] Calling LLM service with email: {context['email']}")

    is_admin_dashboard = http_request.headers.get("x-source") == "omni2-admin-dashboard"

    slack_user_id = None
    slack_channel = None
    slack_message_ts = None
    slack_thread_ts = None

    if request.slack_context:
        slack_user_id = request.slack_context.get("slack_user_id")
        slack_channel = request.slack_context.get("slack_channel")
        slack_message_ts = request.slack_context.get("slack_message_ts")
        slack_thread_ts = request.slack_context.get("slack_thread_ts")

    async def event_stream():
        try:
            # Send welcome message as tokens (same format as LLM)
            welcome_text = welcome['message']
            for char in welcome_text:
                payload = json.dumps({"text": char})
                yield f"event: token\ndata: {payload}\n\n"
            
            # Add newlines after welcome
            newline_payload = json.dumps({"text": "\n\n"})
            yield f"event: token\ndata: {newline_payload}\n\n"
            
            # Now stream LLM response
            async for event in llm_service.ask_stream(
                user_id=context['email'],
                message=request.message,
                is_admin_dashboard=is_admin_dashboard,
            ):
                if event.get("type") == "token":
                    payload = json.dumps({"text": event.get("text", "")})
                    yield f"event: token\ndata: {payload}\n\n"
                elif event.get("type") == "done":
                    yield f"event: done\ndata: {json.dumps(event.get('result', {}))}\n\n"
                elif event.get("type") == "error":
                    yield f"event: error\ndata: {json.dumps({'error': event.get('error', 'Streaming error')})}\n\n"
                    return
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
