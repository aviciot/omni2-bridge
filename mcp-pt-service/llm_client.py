"""LLM Client for MCP PT Service - Multi-Provider Support (Anthropic, Gemini, Groq)."""

import asyncio
import re
import time
from typing import Dict, Any, Optional
from anthropic import AsyncAnthropic
from google import genai
from google.genai import types
from openai import AsyncOpenAI
from logger import logger


class LLMClient:
    """Dual LLM client supporting Anthropic Claude and Google Gemini."""
    
    _semaphore: Optional[asyncio.Semaphore] = None
    
    def __init__(self, provider: str, api_key: str, model: str, max_concurrent: int = 2):
        self.provider = provider
        self.model = model
        
        if provider == "anthropic":
            if not api_key:
                raise ValueError("Anthropic API key not configured")
            self.client = AsyncAnthropic(api_key=api_key)
        elif provider == "gemini":
            if not api_key:
                raise ValueError("Google API key not configured")
            self.client = genai.Client(api_key=api_key)
        elif provider == "groq":
            if not api_key:
                raise ValueError("Groq API key not configured")
            self.client = AsyncOpenAI(
                api_key=api_key,
                base_url="https://api.groq.com/openai/v1",
            )
        else:
            raise ValueError(f"Invalid LLM provider: {provider}")
        
        if LLMClient._semaphore is None:
            LLMClient._semaphore = asyncio.Semaphore(max_concurrent)
        
        logger.info(f"LLM client initialized: {provider} ({model})")
    
    async def generate(self, prompt: str, system_prompt: Optional[str] = None,
                       json_mode: bool = False) -> Dict[str, Any]:
        """Generate response with rate limiting.

        Set json_mode=True when you need a guaranteed-valid JSON response.
        Gemini and OpenAI/Groq enforce this at the API level — no post-processing needed.
        Anthropic has no native JSON mode; the system prompt must instruct JSON output.
        """
        async with LLMClient._semaphore:
            return await self._call(prompt, system_prompt, json_mode=json_mode)

    async def _call(self, prompt: str, system_prompt: Optional[str],
                    json_mode: bool = False) -> Dict[str, Any]:
        """Call LLM API."""
        start = time.time()

        try:
            if self.provider == "anthropic":
                # Anthropic has no native JSON mode — system prompt must enforce it.
                messages = [{"role": "user", "content": prompt}]
                kwargs = {"model": self.model, "max_tokens": 8192, "messages": messages}
                if system_prompt:
                    kwargs["system"] = system_prompt

                response = await self.client.messages.create(**kwargs)
                content = response.content[0].text
                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens
                cost = (input_tokens / 1_000_000 * 3.0) + (output_tokens / 1_000_000 * 15.0)

            elif self.provider == "gemini":
                full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
                gen_config = types.GenerateContentConfig(
                    response_mime_type="application/json" if json_mode else "text/plain"
                )
                response = await self.client.aio.models.generate_content(
                    model=self.model,
                    contents=full_prompt,
                    config=gen_config,
                )
                content = response.text
                # Gemini may embed literal control chars (bare \n, \t) inside string values
                # even in json_mode. Sanitize before returning so json.loads succeeds directly.
                if json_mode and content:
                    content = self._sanitize_control_chars(content)
                input_tokens = response.usage_metadata.prompt_token_count if response.usage_metadata else len(full_prompt) // 4
                output_tokens = response.usage_metadata.candidates_token_count if response.usage_metadata else len(content) // 4
                cost = (input_tokens / 1_000_000 * 0.075) + (output_tokens / 1_000_000 * 0.30)

            elif self.provider == "groq":
                messages = [{"role": "user", "content": prompt}]
                if system_prompt:
                    messages.insert(0, {"role": "system", "content": system_prompt})
                kwargs = {"model": self.model, "max_tokens": 8192, "messages": messages}
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}
                response = await self.client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content
                input_tokens = response.usage.prompt_tokens if response.usage else 0
                output_tokens = response.usage.completion_tokens if response.usage else 0
                cost = 0.0  # Groq pricing is minimal; track as 0

            duration_ms = int((time.time() - start) * 1000)

            logger.info(f"LLM call: {input_tokens}in/{output_tokens}out, {duration_ms}ms, ${cost:.4f}")

            return {
                "content": content,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": cost,
                "duration_ms": duration_ms
            }

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise
    
    def extract_json(self, text: str) -> str:
        """Extract JSON from markdown fences, then repair common LLM output issues."""
        text = text.strip()

        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            raw = text[start:end].strip() if end != -1 else text[start:].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            raw = text[start:end].strip() if end != -1 else text[start:].strip()
        else:
            start = text.find("{")
            if start == -1:
                raise ValueError("No JSON found in response")
            raw = text[start:]

        return self._repair_json(raw)

    @staticmethod
    def _sanitize_control_chars(text: str) -> str:
        """Escape bare control characters that appear inside JSON string values.

        LLMs sometimes embed literal newlines/tabs from multi-line descriptions
        directly inside JSON strings, producing 'Invalid control character' errors.
        This pass re-escapes them while leaving structural characters (outside
        strings) untouched.
        """
        _CTRL = {'\n': '\\n', '\r': '\\r', '\t': '\\t', '\b': '\\b', '\f': '\\f'}
        result = []
        in_string = False
        escape_next = False
        for ch in text:
            if escape_next:
                result.append(ch)
                escape_next = False
                continue
            if ch == '\\' and in_string:
                result.append(ch)
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                result.append(ch)
                continue
            if in_string and ord(ch) < 0x20:
                result.append(_CTRL.get(ch, f'\\u{ord(ch):04x}'))
            else:
                result.append(ch)
        return ''.join(result)

    def _repair_json(self, text: str) -> str:
        """Repair common JSON issues from LLM output: trailing commas, JS comments, truncation."""
        # Strip JS-style single-line comments only when outside string values.
        # A naive re.sub(r'//[^\n]*') would corrupt URLs like https://host/path.
        # Walk character-by-character so we respect string boundaries.
        cleaned = []
        in_str = False
        esc = False
        i = 0
        while i < len(text):
            ch = text[i]
            if esc:
                cleaned.append(ch)
                esc = False
                i += 1
                continue
            if ch == '\\' and in_str:
                cleaned.append(ch)
                esc = True
                i += 1
                continue
            if ch == '"':
                in_str = not in_str
                cleaned.append(ch)
                i += 1
                continue
            if not in_str and ch == '/' and i + 1 < len(text):
                if text[i + 1] == '/':
                    # single-line comment — skip to end of line
                    while i < len(text) and text[i] != '\n':
                        i += 1
                    continue
                if text[i + 1] == '*':
                    # block comment — skip to */
                    i += 2
                    while i < len(text) - 1 and not (text[i] == '*' and text[i + 1] == '/'):
                        i += 1
                    i += 2  # skip */
                    continue
            cleaned.append(ch)
            i += 1
        text = ''.join(cleaned)

        # Escape bare control characters inside string values before any other repair
        text = self._sanitize_control_chars(text)

        # Remove trailing commas before ] or }
        text = re.sub(r',\s*([\]}])', r'\1', text)

        # Find the outermost { ... } to ignore trailing garbage
        brace_start = text.find("{")
        if brace_start == -1:
            raise ValueError("No JSON object found")

        # Walk forward counting braces to find matching close
        depth = 0
        in_string = False
        escape_next = False
        end_pos = -1

        for i, ch in enumerate(text[brace_start:], start=brace_start):
            if escape_next:
                escape_next = False
                continue
            if ch == '\\' and in_string:
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    end_pos = i
                    break

        if end_pos == -1:
            # JSON is truncated — close all open structures
            text = text[brace_start:]
            # Re-strip trailing commas one more time after slicing
            text = re.sub(r',\s*$', '', text.rstrip())
            # Count unclosed braces/brackets and close them
            depth = 0
            bracket_depth = 0
            in_string = False
            escape_next = False
            for ch in text:
                if escape_next:
                    escape_next = False
                    continue
                if ch == '\\' and in_string:
                    escape_next = True
                    continue
                if ch == '"':
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                elif ch == '[':
                    bracket_depth += 1
                elif ch == ']':
                    bracket_depth -= 1
            # If we're inside a string, close it
            if in_string:
                text += '"'
            # Close unclosed brackets and braces
            text += ']' * max(0, bracket_depth)
            text += '}' * max(0, depth)
            return text

        return text[brace_start:end_pos + 1]


_client: Optional[LLMClient] = None

def get_llm_client(provider: str = None, model: str = None) -> LLMClient:
    """Get LLM client with optional provider/model override."""
    from config_service import get_config_service
    
    config_service = get_config_service()
    
    # Use provided or default from config
    if not provider:
        exec_settings = config_service.get_execution_settings()
        provider = exec_settings.get('default_llm_provider', 'gemini')
    
    llm_config = config_service.get_llm_config(provider)
    if not llm_config:
        raise ValueError(f"LLM provider not configured: {provider}")
    
    if not llm_config.get('enabled'):
        raise ValueError(f"LLM provider disabled: {provider}")
    
    api_key = llm_config.get('api_key')
    if not api_key:
        raise ValueError(f"API key not configured for provider: {provider}")
    
    if not model:
        model = llm_config.get('default_model')
    
    max_concurrent = config_service.get_execution_settings().get('max_concurrent_llm_calls', 2)
    
    return LLMClient(provider, api_key, model, max_concurrent)
