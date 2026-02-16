"""
Prompt Guard Service - Core Detection Logic

Supports multiple detection modes:
- regex: Fast pattern matching
- ml: Llama-Prompt-Guard-2-86M model
- hybrid: Regex first, then ML for suspicious content
"""

import re
import hashlib
import time
from typing import Dict, Any, Optional

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

# Try to import ML dependencies
try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    import torch
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logger.warning("ML dependencies not available, using regex-only mode")


class PromptGuardService:
    """Prompt injection detection with configurable modes."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize guard service with config."""
        self.config = config
        self.enabled = config.get("enabled", True)
        self.threshold = config.get("threshold", 0.5)
        self.cache_ttl = config.get("cache_ttl_seconds", 3600)
        self.mode = config.get("mode", "regex")  # regex, ml, hybrid
        self.ml_model = config.get("ml_model", "protectai")  # protectai, llama
        
        # In-memory cache
        self._cache: Dict[str, Dict[str, Any]] = {}
        
        # Compile patterns
        self.patterns = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]
        logger.info(f"✅ Regex patterns loaded ({len(self.patterns)} patterns)")
        
        # Load ML model if needed
        self.model = None
        self.tokenizer = None
        if self.mode in ["ml", "hybrid"] and ML_AVAILABLE:
            self._load_ml_model()
        elif self.mode in ["ml", "hybrid"] and not ML_AVAILABLE:
            logger.error("ML mode requested but dependencies not available, falling back to regex")
            self.mode = "regex"
    
    def _load_ml_model(self):
        """Load ML model based on config."""
        try:
            if self.ml_model == "llama":
                logger.info("Loading Llama-Prompt-Guard-2-86M model...")
                model_name = "meta-llama/Llama-Prompt-Guard-2-86M"
            else:  # protectai
                logger.info("Loading ProtectAI DeBERTa v3 model...")
                model_name = "ProtectAI/deberta-v3-base-prompt-injection-v2"
            
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
            self.model.eval()
            logger.info(f"✅ ML model loaded: {model_name}")
        except Exception as e:
            logger.error(f"Failed to load ML model: {e}", exc_info=True)
            self.model = None
            self.tokenizer = None
    
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
    
    def _check_regex(self, text: str) -> tuple[float, list[str]]:
        """Check text using regex patterns."""
        matches = []
        for pattern in self.patterns:
            match = pattern.search(text)
            if match:
                matches.append(match.group(0))
        
        # Calculate score based on matches
        if matches:
            score = min(0.5 + (len(matches) * 0.2), 0.95)
        else:
            score = 0.0
        
        return score, matches
    
    def _check_ml(self, text: str) -> tuple[float, str]:
        """Check text using ML model."""
        if not self.model or not self.tokenizer:
            return 0.0, "ML model not available"
        
        try:
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probs = torch.softmax(logits, dim=-1)
                
                # Model outputs: [safe, injection]
                injection_prob = probs[0][1].item()
            
            return injection_prob, "ML detection"
        
        except Exception as e:
            logger.error(f"ML detection error: {e}", exc_info=True)
            return 0.0, f"ML error: {str(e)}"
    
    async def check_prompt(self, text: str, user_id: int = None) -> Dict[str, Any]:
        """
        Check if text contains prompt injection.
        
        Returns:
            {
                "safe": bool,
                "score": float,
                "action": str,
                "reason": str,
                "method": str,  # regex, ml, hybrid
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
                "method": "none",
                "cached": False,
                "latency_ms": 0,
            }
        
        # Check cache
        # CACHE DISABLED FOR TESTING
        # cached_result = self._check_cache(text)
        # if cached_result:
        #     cached_result["cached"] = True
        #     return cached_result
        
        try:
            score = 0.0
            reason = "No injection detected"
            method = self.mode
            
            if self.mode == "regex":
                # Regex only
                score, matches = self._check_regex(text)
                if matches:
                    reason = f"Pattern match: {matches[0][:50]}"
            
            elif self.mode == "ml":
                # ML only
                score, ml_reason = self._check_ml(text)
                reason = ml_reason
            
            elif self.mode == "hybrid":
                # Run BOTH regex AND ML
                logger.info(f"🔥 HYBRID MODE: Running both regex and ML")
                regex_score, matches = self._check_regex(text)
                logger.info(f"Regex score: {regex_score}")
                ml_score, ml_reason = self._check_ml(text)
                logger.info(f"ML score: {ml_score}")
                
                # Take higher score
                score = max(regex_score, ml_score)
                reason = f"Regex: {regex_score:.2f}, ML: {ml_score:.2f}"
                if matches:
                    reason += f" | Pattern: {matches[0][:30]}"
            
            is_safe = score < self.threshold
            latency_ms = int((time.time() - start_time) * 1000)
            
            result = {
                "safe": is_safe,
                "score": round(score, 4),
                "reason": reason,
                "method": method,
                "cached": False,
                "latency_ms": latency_ms,
            }
            
            # Cache result (DISABLED)
            # self._update_cache(text, result)
            
            logger.info(
                "Prompt checked",
                user_id=user_id,
                score=result["score"],
                method=method,
                latency_ms=latency_ms,
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error checking prompt: {e}", exc_info=True)
            return {
                "safe": True,
                "score": 0.0,
                "reason": f"Error: {str(e)}",
                "method": "error",
                "cached": False,
                "latency_ms": int((time.time() - start_time) * 1000),
            }
    
    def reload_config(self, new_config: Dict[str, Any]):
        """Reload configuration without restarting service."""
        logger.info("Reloading configuration", new_config=new_config)
        
        old_enabled = self.enabled
        old_mode = self.mode
        old_ml_model = getattr(self, 'ml_model', 'protectai')
        
        self.config = new_config
        self.enabled = new_config.get("enabled", True)
        self.threshold = new_config.get("threshold", 0.5)
        self.cache_ttl = new_config.get("cache_ttl_seconds", 3600)
        self.mode = new_config.get("mode", "regex")
        self.ml_model = new_config.get("ml_model", "protectai")
        
        # Clear cache
        self._cache.clear()
        
        # Reload ML model if mode or model changed
        if self.mode in ["ml", "hybrid"] and ML_AVAILABLE:
            if old_mode == "regex" or old_ml_model != self.ml_model:
                self._load_ml_model()
        
        if old_enabled != self.enabled:
            status = "ENABLED" if self.enabled else "DISABLED"
            logger.warning(f"Prompt guard {status}")
        
        if old_mode != self.mode:
            logger.warning(f"Detection mode changed: {old_mode} -> {self.mode}")
        
        if old_ml_model != self.ml_model:
            logger.warning(f"ML model changed: {old_ml_model} -> {self.ml_model}")
