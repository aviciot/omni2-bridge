"""
WebSocket Chat Router - LLM Conversations with Conversation Tracking
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from uuid import uuid4
import json
import time
from sqlalchemy import text
from app.services.llm_service import get_llm_service, LLMService
from app.services.chat_context_service import get_chat_context_service, ChatContextService
from app.services.flow_tracker import get_flow_tracker, FlowTracker
from app.services.activity_tracker import get_activity_tracker
from app.services.ws_connection_manager import get_ws_manager
from app.services.prompt_guard_client import get_prompt_guard_client
from app.database import get_db
from app.utils.logger import logger

router = APIRouter()

@router.websocket("/ws/chat")
async def chat_websocket(
    websocket: WebSocket,
    llm_service: LLMService = Depends(get_llm_service),
    context_service: ChatContextService = Depends(get_chat_context_service),
    flow_tracker: FlowTracker = Depends(get_flow_tracker),
):
    """
    WebSocket endpoint for LLM chat with automatic conversation tracking.
    
    Connection lifecycle:
    1. Connect → Generate conversation_id
    2. Multiple messages → All share same conversation_id
    3. Disconnect → Conversation ends
    
    Message Protocol:
    Client → Server: {"type": "message", "text": "Hello"}
    Server → Client: {"type": "welcome", "text": "..."}
                     {"type": "token", "text": "H"}
                     {"type": "done", "result": {...}}
                     {"type": "error", "error": "..."}
    """
    
    logger.info("[WS-CHAT] 🔌 New WebSocket chat connection")
    
    # Extract user_id from Traefik header
    user_id_header = websocket.headers.get("x-user-id")
    
    if not user_id_header:
        logger.warning("[WS-CHAT] ❌ Missing X-User-Id header")
        await websocket.close(code=1008, reason="Missing X-User-Id header")
        return
    
    try:
        user_id = int(user_id_header)
        logger.info(f"[WS-CHAT] ✓ User ID: {user_id}")
    except ValueError:
        logger.error(f"[WS-CHAT] ❌ Invalid X-User-Id: {user_id_header}")
        await websocket.close(code=1008, reason="Invalid X-User-Id header")
        return
    
    # Load user context
    try:
        context = await context_service.load_user_context(user_id)
        logger.info(f"[WS-CHAT] 👤 User: {context['email']}, Role: {context['role_name']}")
    except Exception as e:
        logger.error(f"[WS-CHAT] ❌ Failed to load context: {str(e)}")
        await websocket.close(code=1011, reason=f"Failed to load user context: {str(e)}")
        return
    
    # Check if user is blocked
    is_blocked, block_reason = await context_service.check_user_blocked(user_id)
    if is_blocked:
        logger.warning(f"[WS-CHAT] 🚫 User {user_id} is blocked: {block_reason}")
        await websocket.close(code=1008, reason=f"Access blocked: {block_reason}")
        return
    
    # Check if user account is active
    if not context['active']:
        logger.warning(f"[WS-CHAT] ❌ User {user_id} account inactive")
        await websocket.close(code=1008, reason="Account inactive")
        return
    
    # Accept connection
    await websocket.accept()
    logger.info("[WS-CHAT] ✅ WebSocket connection accepted")

    # Register connection with WebSocket manager for instant blocking
    ws_manager = get_ws_manager()
    if ws_manager:
        await ws_manager.connect(user_id, websocket)

    # Generate conversation_id for this WebSocket connection
    conversation_id = uuid4()
    logger.info(f"[WS-CHAT] 🆔 Conversation started - ID: {conversation_id}, User: {context['email']}")
    
    # Send welcome message (sent ONCE per conversation)
    welcome = await context_service.get_welcome_message(user_id, context['role_id'])
    logger.info(f"[WS-CHAT] 📤 SENDING WELCOME MESSAGE (conversation_id={conversation_id})")
    await websocket.send_json({"type": "token", "text": welcome['message'] + "\n\n"})
    logger.info(f"[WS-CHAT] ✅ WELCOME MESSAGE SENT (conversation_id={conversation_id})")
    
    # Get available MCPs
    available_mcps = await context_service.get_available_mcps(context['mcp_access'])
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
                
                if message_data.get("type") != "message":
                    continue
                
                user_message = message_data.get("text", "")
                if not user_message:
                    continue
                
                # Check for prompt injection (with role bypass)
                prompt_guard = get_prompt_guard_client()
                logger.info(f"[WS-CHAT] 🛡️ Prompt guard client: {prompt_guard is not None}")
                
                if prompt_guard:
                    try:
                        # Try cached config first, fallback to DB
                        from app.services.prompt_guard_config_cache import get_cached_config
                        guard_config = get_cached_config()
                        
                        if not guard_config:
                            logger.info("[WS-CHAT] 🛡️ Loading config from DB")
                            async for db_check in get_db():
                                config_result = await db_check.execute(
                                    text("SELECT config_value FROM omni2.omni2_config WHERE config_key = 'prompt_guard' AND is_active = true")
                                )
                                guard_config = config_result.scalar()
                                break
                        else:
                            logger.info("[WS-CHAT] 🛡️ Using cached config")
                        
                        if not guard_config:
                            guard_config = {
                                "enabled": True,
                                "threshold": 0.5,
                                "bypass_roles": [],
                                "actions": {"warn": True, "block": False},
                                "behavioral_tracking": {"enabled": True, "warning_threshold": 2, "block_threshold": 5, "window_hours": 24}
                            }
                            logger.info("[WS-CHAT] 🛡️ Using default guard config")
                        
                        bypass_roles = guard_config.get("bypass_roles", [])
                        guard_enabled = guard_config.get("enabled", True)
                        
                        logger.info(f"[WS-CHAT] 🛡️ Guard enabled: {guard_enabled}, bypass roles: {bypass_roles}, user role: {context.get('role_name')}")
                        
                        # Check if guard is enabled and user role is not bypassed
                        if guard_enabled and context.get('role_name') not in bypass_roles:
                            logger.info(f"[WS-CHAT] 🛡️ Checking prompt: '{user_message[:50]}...'")
                            guard_result = await prompt_guard.check_prompt(user_message, user_id)
                            logger.info(f"[WS-CHAT] 🛡️ Guard result: {guard_result}")
                            
                            if not guard_result["safe"]:
                                logger.warning(f"[WS-CHAT] 🚨 INJECTION DETECTED! Score: {guard_result['score']}")
                                
                                score = guard_result["score"]
                                action = "allow"
                                violation_count = 0
                                
                                # Behavioral tracking
                                behavioral_config = guard_config.get("behavioral_tracking", {})
                                if behavioral_config.get("enabled", False):
                                    window_hours = behavioral_config.get("window_hours", 24)
                                    async for db_count in get_db():
                                        count_result = await db_count.execute(
                                            text(
                                                "SELECT COUNT(*) FROM omni2.prompt_injection_log "
                                                "WHERE user_id = :user_id "
                                                "AND detected_at > NOW() - INTERVAL '1 hour' * :hours "
                                                "AND action IN ('warn', 'block')"
                                            ),
                                            {"user_id": user_id, "hours": window_hours}
                                        )
                                        violation_count = count_result.scalar() or 0
                                        break
                                    
                                    logger.info(f"[WS-CHAT] 📊 User {user_id} violations: {violation_count} in last {window_hours}h")
                                    
                                    warning_threshold = behavioral_config.get("warning_threshold", 2)
                                    block_threshold = behavioral_config.get("block_threshold", 5)
                                    
                                    if violation_count >= block_threshold:
                                        action = "block"
                                        logger.warning(f"[WS-CHAT] 🚫 Auto-blocking (violations: {violation_count})")
                                    elif violation_count >= warning_threshold:
                                        action = "warn"
                                        logger.warning(f"[WS-CHAT] ⚠️ Escalating to warn (violations: {violation_count})")
                                
                                # Apply immediate action rules
                                actions_config = guard_config.get("actions", {})
                                if actions_config.get("block", False):
                                    action = "block"
                                elif actions_config.get("warn", True) and action == "allow":
                                    action = "warn"
                                
                                # Log to database
                                async for db_log in get_db():
                                    await db_log.execute(
                                        text(
                                            "INSERT INTO omni2.prompt_injection_log "
                                            "(user_id, message, injection_score, action, detected_at) "
                                            "VALUES (:user_id, :message, :score, :action, NOW())"
                                        ),
                                        {"user_id": user_id, "message": user_message[:500], "score": score, "action": action}
                                    )
                                    await db_log.commit()
                                    
                                    # Block user if threshold reached
                                    if action == "block" and violation_count + 1 >= behavioral_config.get("block_threshold", 5):
                                        await db_log.execute(
                                            text(
                                                "INSERT INTO omni2.user_blocks "
                                                "(user_id, is_blocked, block_reason, custom_block_message, blocked_at, blocked_by) "
                                                "VALUES (:user_id, true, :reason, :message, NOW(), NULL) "
                                                "ON CONFLICT (user_id) DO UPDATE SET "
                                                "is_blocked = true, block_reason = :reason, custom_block_message = :message, blocked_at = NOW()"
                                            ),
                                            {
                                                "user_id": user_id,
                                                "reason": "Repeated prompt injection violations",
                                                "message": "Your account has been blocked due to multiple security policy violations."
                                            }
                                        )
                                        await db_log.commit()
                                        logger.warning(f"[WS-CHAT] 🚫 User {user_id} blocked (violations: {violation_count + 1})")
                                    
                                    break
                                
                                logger.info(f"[WS-CHAT] 📝 Logged: action={action}, score={score}, violations={violation_count}")
                                
                                # Publish notification
                                from app.database import redis_client
                                if redis_client:
                                    notification_data = {
                                        "type": "prompt_guard_violation",
                                        "data": {
                                            "user_id": user_id,
                                            "user_email": context.get('email'),
                                            "score": score,
                                            "action": action,
                                            "violation_count": violation_count,
                                            "message_preview": user_message[:50] + "..." if len(user_message) > 50 else user_message,
                                            "timestamp": time.time()
                                        }
                                    }
                                    await redis_client.publish("system_events", json.dumps(notification_data))
                                    logger.info("[WS-CHAT] 📡 Published notification")
                                    
                                    # Publish user block event if threshold reached
                                    if action == "block" and violation_count + 1 >= behavioral_config.get("block_threshold", 5):
                                        block_event = {
                                            "user_id": user_id,
                                            "custom_message": "Your account has been blocked due to multiple security policy violations.",
                                            "blocked_by": "system",
                                            "timestamp": time.time()
                                        }
                                        await redis_client.publish("user_blocked", json.dumps(block_event))
                                        logger.warning(f"[WS-CHAT] 📡 Published user_blocked event for user {user_id}")
                                        
                                        # Publish system notification
                                        user_blocked_notification = {
                                            "type": "prompt_guard_user_blocked",
                                            "data": {
                                                "user_id": user_id,
                                                "user_email": context.get('email'),
                                                "violation_count": violation_count + 1,
                                                "timestamp": time.time()
                                            }
                                        }
                                        await redis_client.publish("system_events", json.dumps(user_blocked_notification))
                                        logger.warning(f"[WS-CHAT] 📡 Published prompt_guard_user_blocked notification")
                                
                                # Handle action
                                if action == "block":
                                    logger.warning(f"[WS-CHAT] 🚫 Blocked (score: {score}, violations: {violation_count})")
                                    await websocket.send_json({"type": "blocked", "message": "Message blocked due to security policy violation"})
                                    continue
                                elif action == "warn":
                                    logger.warning(f"[WS-CHAT] ⚠️ Warning (score: {score}, violations: {violation_count})")
                                    await websocket.send_json({"type": "warning", "message": "Suspicious content detected"})
                            else:
                                logger.info(f"[WS-CHAT] ✅ Passed (score: {guard_result['score']})")
                        else:
                            if not guard_enabled:
                                logger.info("[WS-CHAT] 🛡️ Guard disabled")
                            else:
                                logger.info(f"[WS-CHAT] 🛡️ Role '{context.get('role_name')}' bypassed")
                    
                    except Exception as e:
                        logger.error(f"[WS-CHAT] ❌ Guard error: {e}")
                else:
                    logger.warning("[WS-CHAT] ⚠️ Guard client not available")

                
                # Check usage limits before processing
                usage = await context_service.check_usage_limit(user_id, context['cost_limit_daily'])
                if not usage['allowed']:
                    await websocket.send_json({
                        "type": "error",
                        "error": f"Daily limit exceeded. Used ${usage['cost_used']:.2f} of ${usage['cost_limit']:.2f}"
                    })
                    continue
                
                # Create new session_id for this message
                session_id = uuid4()
                logger.info(f"[WS-CHAT] 💬 New message - Session: {session_id}, Conversation: {conversation_id}")
                
                # Track sequence number and record user message
                activity_tracker = get_activity_tracker()
                async for db in get_db():
                    result = await db.execute(
                        text("SELECT COALESCE(MAX(sequence_num), 0) + 1 FROM omni2.user_activities WHERE conversation_id = :conv_id"),
                        {"conv_id": conversation_id}
                    )
                    sequence_num = result.scalar()
                    
                    await activity_tracker.record_user_message(
                        db=db,
                        conversation_id=conversation_id,
                        session_id=session_id,
                        user_id=user_id,
                        sequence_num=sequence_num,
                        message=user_message
                    )
                    break
                
                # Log flow checkpoints
                async for db in get_db():
                    node1 = await flow_tracker.log_event(session_id, user_id, "auth_check", db=db, status="passed")
                    node2 = await flow_tracker.log_event(session_id, user_id, "block_check", parent_id=node1, db=db, status="passed")
                    node3 = await flow_tracker.log_event(session_id, user_id, "usage_check", parent_id=node2, db=db, remaining=usage['remaining'])
                    node4 = await flow_tracker.log_event(session_id, user_id, "mcp_permission_check", parent_id=node3, db=db,
                                                         mcp_access=str(context['mcp_access']),
                                                         available_mcps=str([m['name'] for m in available_mcps]))
                    node5 = await flow_tracker.log_event(session_id, user_id, "tool_filter", parent_id=node4, db=db,
                                                         tool_restrictions=str(context['tool_restrictions']))
                    llm_node = await flow_tracker.log_event(session_id, user_id, "llm_thinking", parent_id=node5, db=db)
                    break
                
                # Track tool calls
                tool_call_start_time = {}
                tool_sequence = sequence_num
                
                # Stream LLM response
                async for event in llm_service.ask_stream(
                    user_id=context['email'],
                    message=user_message,
                    is_admin_dashboard=False,
                    mcp_access=context['mcp_access'],
                    tool_restrictions=context['tool_restrictions'],
                ):
                    if event.get("type") == "token":
                        await websocket.send_json({"type": "token", "text": event.get("text", "")})
                    
                    elif event.get("type") == "tool_call":
                        mcp_server = event.get("mcp")
                        tool_name = event.get("tool")
                        
                        async for db in get_db():
                            await flow_tracker.log_event(
                                session_id, user_id, "tool_call",
                                parent_id=llm_node, db=db,
                                mcp=mcp_server, tool=tool_name
                            )
                            
                            # Record tool call activity
                            tool_sequence += 1
                            await activity_tracker.record_tool_call(
                                db=db,
                                conversation_id=conversation_id,
                                session_id=session_id,
                                user_id=user_id,
                                sequence_num=tool_sequence,
                                mcp_server=mcp_server,
                                tool_name=tool_name,
                                parameters=event.get("parameters", {})
                            )
                            
                            # Track start time for duration calculation
                            tool_key = f"{mcp_server}.{tool_name}"
                            tool_call_start_time[tool_key] = time.time()
                            break
                    
                    elif event.get("type") == "done":
                        result = event.get('result', {})
                        
                        # Record tool responses (if any tools were called)
                        if tool_call_start_time:
                            async for db in get_db():
                                for tool_key, start_time in tool_call_start_time.items():
                                    mcp_server, tool_name = tool_key.split(".")
                                    duration_ms = int((time.time() - start_time) * 1000)
                                    tool_sequence += 1
                                    
                                    await activity_tracker.record_tool_response(
                                        db=db,
                                        conversation_id=conversation_id,
                                        session_id=session_id,
                                        user_id=user_id,
                                        sequence_num=tool_sequence,
                                        mcp_server=mcp_server,
                                        tool_name=tool_name,
                                        status="success",
                                        duration_ms=duration_ms
                                    )
                                break
                        
                        # Record assistant response
                        async for db in get_db():
                            await flow_tracker.log_event(
                                session_id, user_id, "llm_complete",
                                parent_id=llm_node, db=db,
                                tokens=result.get("tokens_output", 0)
                            )
                            
                            # Record assistant response activity
                            tool_sequence += 1
                            await activity_tracker.record_assistant_response(
                                db=db,
                                conversation_id=conversation_id,
                                session_id=session_id,
                                user_id=user_id,
                                sequence_num=tool_sequence,
                                message=result.get("answer", ""),
                                tokens_used=result.get("tokens_output", 0),
                                model=result.get("model")
                            )
                            
                            # Save flow with conversation_id
                            await flow_tracker.save_to_db(session_id, user_id, db, conversation_id=conversation_id)
                            logger.info(f"[WS-CHAT] ✅ Message complete - Session: {session_id}, Conversation: {conversation_id}")
                            break
                        await websocket.send_json({"type": "done", "result": result})
                    
                    elif event.get("type") == "error":
                        async for db in get_db():
                            await flow_tracker.log_event(session_id, user_id, "error", db=db, error=event.get('error'))
                            await flow_tracker.save_to_db(session_id, user_id, db, conversation_id=conversation_id)
                            break
                        await websocket.send_json({"type": "error", "error": event.get('error', 'Streaming error')})
                        break
                
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "error": "Invalid JSON"})
            except Exception as e:
                logger.error(f"[WS-CHAT] Message processing error: {str(e)}")
                await websocket.send_json({"type": "error", "error": str(e)})
    
    except WebSocketDisconnect:
        logger.info(f"[WS-CHAT] 🔌 User disconnected - Conversation: {conversation_id}, User: {context['email']}")
    except Exception as e:
        logger.error(f"[WS-CHAT] ❌ Connection error: {str(e)}")
    finally:
        # Unregister connection from WebSocket manager
        ws_manager = get_ws_manager()
        if ws_manager:
            await ws_manager.disconnect(user_id, websocket)

        logger.info(f"[WS-CHAT] 🆔 Conversation ended - ID: {conversation_id}")
