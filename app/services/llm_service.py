"""
LLM Service

Handles communication with Claude (Anthropic) for intelligent MCP routing.
"""

from typing import Dict, List, Optional, Any
import os
import anthropic
from anthropic.types import Message, ToolUseBlock, TextBlock

from app.config import settings
from app.services.mcp_client import get_mcp_client
from app.services.user_service import get_user_service
from app.utils.logger import logger


class LLMService:
    """Service for LLM-powered MCP routing and question answering."""
    
    def __init__(self):
        """Initialize LLM service with Anthropic client."""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key or api_key == "your-anthropic-api-key-here":
            raise ValueError(
                "ANTHROPIC_API_KEY not set. Get one from https://console.anthropic.com/"
            )
        
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
        self.max_tokens = int(os.getenv("ANTHROPIC_MAX_TOKENS", "4096"))
        self.mcp_client = get_mcp_client()
        self.user_service = get_user_service()
        
    async def build_system_prompt(self, user_id: str) -> str:
        """
        Build dynamic system prompt based on user's permissions.
        
        Args:
            user_id: User email address
            
        Returns:
            System prompt string
        """
        user = self.user_service.get_user(user_id)
        allowed_mcps = self.user_service.get_allowed_mcps(user_id)
        allowed_domains = self.user_service.get_allowed_domains(user_id)
        
        # Get available tools for user's allowed MCPs
        tools_catalog = []
        
        if allowed_mcps == "*":
            # Admin - get all MCPs
            all_tools = await self.mcp_client.list_tools()
            for mcp_name, mcp_data in all_tools.get("servers", {}).items():
                if mcp_data.get("status") == "healthy":
                    for tool in mcp_data.get("tools", []):
                        tools_catalog.append({
                            "mcp": mcp_name,
                            "name": tool["name"],
                            "description": tool["description"],
                        })
        else:
            # Regular user - only allowed MCPs
            for mcp_name in allowed_mcps:
                try:
                    mcp_tools = await self.mcp_client.list_tools(mcp_name)
                    for tool in mcp_tools.get("servers", {}).get(mcp_name, {}).get("tools", []):
                        tools_catalog.append({
                            "mcp": mcp_name,
                            "name": tool["name"],
                            "description": tool["description"],
                        })
                except Exception as e:
                    logger.warning(f"Could not load tools from {mcp_name}", error=str(e))
        
        # Build prompt
        prompt = f"""You are OMNI2, an intelligent MCP (Model Context Protocol) router and assistant.

User: {user.get('name', user_id)} ({user.get('role', 'user')})

AVAILABLE TOOLS:
You can call these MCP tools to help the user:
"""
        
        for tool in tools_catalog:
            prompt += f"\n- {tool['mcp']}.{tool['name']}: {tool['description']}"
        
        prompt += f"""

ALLOWED KNOWLEDGE DOMAINS:
"""
        
        if allowed_domains == "*":
            prompt += "- You can answer questions about ANY topic.\n"
        else:
            for domain in allowed_domains:
                domain_desc = {
                    "general_knowledge": "General questions (TV shows, history, etc.)",
                    "python_help": "Python programming help and code examples",
                    "code_review": "Code review and best practices",
                    "database_help": "Database concepts and SQL help",
                    "sql_help": "SQL query writing and optimization",
                    "testing_help": "Software testing strategies",
                    "data_analysis": "Data analysis and interpretation",
                }.get(domain, domain)
                prompt += f"- {domain_desc}\n"
        
        prompt += """
RULES:
1. If the question requires MCP tool → Use function calling to execute the tool
2. If the question is general knowledge (in allowed domains) → Answer directly
3. If the question is outside your scope → Politely explain what you CAN help with
4. Always be helpful, accurate, and concise
5. If a tool fails, explain the error and suggest alternatives

When calling tools, use the exact tool name and provide all required arguments.
"""
        
        return prompt
    
    async def build_tools_for_claude(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Build Claude function definitions from MCP tools.
        
        Args:
            user_id: User email address
            
        Returns:
            List of tool definitions for Claude
        """
        allowed_mcps = self.user_service.get_allowed_mcps(user_id)
        claude_tools = []
        
        if allowed_mcps == "*":
            all_tools = await self.mcp_client.list_tools()
            for mcp_name, mcp_data in all_tools.get("servers", {}).items():
                if mcp_data.get("status") == "healthy":
                    for tool in mcp_data.get("tools", []):
                        claude_tools.append({
                            "name": f"{mcp_name}__{tool['name']}",  # Prefix with MCP name
                            "description": f"[{mcp_name}] {tool['description']}",
                            "input_schema": tool["inputSchema"],
                        })
        else:
            for mcp_name in allowed_mcps:
                try:
                    mcp_tools = await self.mcp_client.list_tools(mcp_name)
                    for tool in mcp_tools.get("servers", {}).get(mcp_name, {}).get("tools", []):
                        claude_tools.append({
                            "name": f"{mcp_name}__{tool['name']}",
                            "description": f"[{mcp_name}] {tool['description']}",
                            "input_schema": tool["inputSchema"],
                        })
                except Exception as e:
                    logger.warning(f"Could not load tools from {mcp_name}", error=str(e))
        
        return claude_tools
    
    async def ask(self, user_id: str, message: str) -> Dict[str, Any]:
        """
        Process user question with LLM routing.
        
        Args:
            user_id: User email address
            message: User's question
            
        Returns:
            Response dict with answer and metadata
        """
        logger.info(
            "Processing LLM request",
            user=user_id,
            message=message[:100],
        )
        
        # Build system prompt and tools
        system_prompt = await self.build_system_prompt(user_id)
        claude_tools = await self.build_tools_for_claude(user_id)
        
        # Call Claude
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system_prompt,
                tools=claude_tools if claude_tools else None,
                messages=[
                    {"role": "user", "content": message}
                ],
            )
            
            # Process response
            result = await self._process_claude_response(response, user_id, message)
            
            logger.info(
                "LLM request completed",
                user=user_id,
                has_tool_calls=result.get("tool_calls", 0) > 0,
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "LLM request failed",
                user=user_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
    
    async def _process_claude_response(
        self, 
        response: Message,
        user_id: str,
        original_message: str
    ) -> Dict[str, Any]:
        """
        Process Claude's response, handling tool calls if needed.
        
        Args:
            response: Claude response message
            user_id: User email address
            original_message: The original user question
            
        Returns:
            Processed response dict
        """
        result = {
            "answer": "",
            "tool_calls": 0,
            "tools_used": [],
            "raw_response": None,
        }
        
        # Check for tool use
        tool_uses = [block for block in response.content if isinstance(block, ToolUseBlock)]
        
        if tool_uses:
            # Execute tool calls
            tool_results = []
            
            for tool_use in tool_uses:
                tool_full_name = tool_use.name  # e.g., "github_mcp__search_repositories"
                mcp_name, tool_name = tool_full_name.split("__", 1)
                
                logger.info(
                    "Executing MCP tool",
                    user=user_id,
                    mcp=mcp_name,
                    tool=tool_name,
                )
                
                try:
                    # Call the actual MCP tool
                    tool_result = await self.mcp_client.call_tool(
                        server_name=mcp_name,
                        tool_name=tool_name,
                        arguments=tool_use.input,
                    )
                    
                    tool_results.append({
                        "mcp": mcp_name,
                        "tool": tool_name,
                        "success": True,
                        "result": tool_result,
                    })
                    
                    result["tools_used"].append(f"{mcp_name}.{tool_name}")
                    
                except Exception as e:
                    logger.error(
                        "Tool execution failed",
                        user=user_id,
                        mcp=mcp_name,
                        tool=tool_name,
                        error=str(e),
                    )
                    tool_results.append({
                        "mcp": mcp_name,
                        "tool": tool_name,
                        "success": False,
                        "error": str(e),
                    })
            
            result["tool_calls"] = len(tool_uses)
            result["tool_results"] = tool_results
            
            # Send tool results back to Claude for final answer
            final_response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[
                    {"role": "user", "content": original_message},
                    {"role": "assistant", "content": response.content},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_use.id,
                                "content": str(tool_res.get("result", tool_res.get("error")))
                            }
                            for tool_use, tool_res in zip(tool_uses, tool_results)
                        ]
                    }
                ],
            )
            
            # Extract final text answer
            text_blocks = [block for block in final_response.content if isinstance(block, TextBlock)]
            result["answer"] = "\n".join(block.text for block in text_blocks)
            
        else:
            # No tool calls - direct answer
            text_blocks = [block for block in response.content if isinstance(block, TextBlock)]
            result["answer"] = "\n".join(block.text for block in text_blocks)
        
        return result


# Global LLM service instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """
    Get or create the global LLM service instance.
    
    Returns:
        LLMService instance
    """
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
