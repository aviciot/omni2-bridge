"""
Prompt Guard Service - Core Detection Logic

Uses regex pattern matching for prompt injection detection (lightweight).
Optional: Can load Llama model if transformers/torch are installed.
"""

import re
import hashlib
import time
from typing import Dict, Any

from config import settings
from logger import logger


# Prompt injection patterns
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|above|prior)\s+instructions?",
    r"disregard\s+(all\s+)?(previous|above|prior)\s+(instructions?|rules?|commands?)",
    r"forget\s+(all\s+)?(previous|above|prior)\s+instructions?",
    r"you\s+are\s+now\s+(?:a|an)\s+\w+",
    r"new\s+instructions?\s*:",
    r"system\s+prompt\s*:",
    r"<\|im_start\|>",
    r"<\|im_end\|>",
    r"\[INST\]",
    r"\[/INST\]",
    r"reveal\s+(?:your|the)\s+(?:system\s+)?prompt",
    r"what\s+(?:are|is)\s+your\s+(?:system\s+)?instructions?",
    r"bypass\s+(?:all\s+)?(?:security|safety|filters?)",
]


class PromptGuardService:
    """Lightweight prompt injection detection using regex patterns."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize guard service with config."""
        self.config = config
        self.enabled = config.get("enabled", True)
        self.threshold = config.get("threshold", 0.5)
        self.cache_ttl = config.get("cache_ttl_seconds", 3600)
        
        # In-memory cache
        self._cache: Dict[str, Dict[str, Any]] = {}
        
        # Compile patterns
        self.patterns = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]
        
        logger.info(f"✅ Pattern-based guard loaded ({len(self.patterns)} patterns)")
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key from text."""
        return hashlib.sha256(text.encode()).hexdigest()
    
    def _check_cache(self, text: str) -> Dict[str, Any] | None:
        """Check if result is cached."""
        cache_key = self._get_cache_key(text)
        
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if time.time() - cached["timestamp"] < self.cache_ttl:
                return cached["result"]
            else:
                del self._cache[cache_key]
        
        return None
    
    def _update_cache(self, text: str, result: Dict[str, Any]):
        """Update cache with new result."""
        cache_key = self._get_cache_key(text)
        self._cache[cache_key] = {
            "result": result,
            "timestamp": time.time(),
        }
        
        # Cleanup if too large
        if len(self._cache) > 10000:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k]["timestamp"])
            del self._cache[oldest_key]
    
    async def check_prompt(self, text: str, user_id: int = None) -> Dict[str, Any]:
        """
        Check if text contains prompt injection using pattern matching.
        
        Returns:
            {
                "safe": bool,
                "score": float,
                "action": str,
                "reason": str,
                "cached": bool,
                "latency_ms": int,
            }
        """
        start_time = time.time()
        
        if not self.enabled:
            return {
                "safe": True,
                "score": 0.0,
                "reason": "Guard disabled",
                "cached": False,
                "latency_ms": 0,
            }
        
        # Check cache
        cached_result = self._check_cache(text)
        if cached_result:
            cached_result["cached"] = True
            return cached_result
        
        try:
            # Check patterns
            matches = []
            for pattern in self.patterns:
                match = pattern.search(text)
                if match:
                    matches.append(match.group(0))
            
            # Calculate score based on matches
            if matches:
                # Score: 0.6 for 1 match, 0.8 for 2+, 0.9 for 3+
                score = min(0.5 + (len(matches) * 0.2), 0.95)
            else:
                score = 0.0
            
            is_safe = score < self.threshold
            
            if not is_safe:
                reason = f"Pattern match detected: {matches[0][:50]}" if matches else "Suspicious content"
            else:
                reason = "No injection detected"
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            result = {
                "safe": is_safe,
                "score": round(score, 4),
                "reason": reason,
                "cached": False,
                "latency_ms": latency_ms,
            }
            
            # Cache result
            self._update_cache(text, result)
            
            logger.info(
                "Prompt checked",
                user_id=user_id,
                score=result["score"],
                latency_ms=latency_ms,
                matches=len(matches),
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error checking prompt: {e}", exc_info=True)
            return {
                "safe": True,
                "score": 0.0,
                "reason": f"Error: {str(e)}",
                "cached": False,
                "latency_ms": int((time.time() - start_time) * 1000),
            }
    
    def reload_config(self, new_config: Dict[str, Any]):
        """Reload configuration without restarting service."""
        logger.info("Reloading configuration", new_config=new_config)
        
        old_enabled = self.enabled
        self.config = new_config
        self.enabled = new_config.get("enabled", True)
        self.threshold = new_config.get("threshold", 0.5)
        self.cache_ttl = new_config.get("cache_ttl_seconds", 3600)
        
        # Clear cache
        self._cache.clear()
        
        if old_enabled != self.enabled:
            status = "ENABLED" if self.enabled else "DISABLED"
            logger.warning(f"Prompt guard {status}")
