"""MCP PT Scanner - PII, Secrets, and Security Testing."""

import re
import time
import httpx
from typing import Dict, Any, List
from logger import logger

try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine
    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False
    logger.info("Presidio library not installed — using regex fallback for PII detection")


class MCPPTScanner:
    """MCP Penetration Testing Scanner."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get("enabled", True)
        self.tools = config.get("tools", {})
        self.scan_depth = config.get("scan_depth", "standard")
        
        # Initialize Presidio
        if PRESIDIO_AVAILABLE and self.tools.get("presidio"):
            self.presidio_analyzer = AnalyzerEngine()
            self.presidio_anonymizer = AnonymizerEngine()
            logger.info("Presidio initialized")
        else:
            self.presidio_analyzer = None
            self.presidio_anonymizer = None
        
        # PII Patterns (fallback if Presidio unavailable)
        self.pii_patterns = {
            "credit_card": re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'),
            "ssn": re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
            "email": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            "phone": re.compile(r'\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'),
        }
        
        # Secrets Patterns
        self.secrets_patterns = {
            "aws_key": re.compile(r'AKIA[0-9A-Z]{16}'),
            "github_token": re.compile(r'ghp_[a-zA-Z0-9]{36}'),
            "api_key": re.compile(r'sk-[a-zA-Z0-9]{48}'),
            "password": re.compile(r'password\s*[:=]\s*["\']?([^"\'\s]+)["\']?', re.IGNORECASE),
        }
    
    def scan_pii(self, text: str) -> Dict[str, Any]:
        """Scan text for PII using Presidio or regex."""
        findings = []
        
        if self.presidio_analyzer:
            # Use Presidio (ML-based)
            results = self.presidio_analyzer.analyze(
                text=text,
                language="en",
                entities=["CREDIT_CARD", "EMAIL_ADDRESS", "PHONE_NUMBER", "US_SSN"]
            )
            
            for result in results:
                findings.append({
                    "type": result.entity_type,
                    "score": result.score,
                    "start": result.start,
                    "end": result.end,
                    "text": text[result.start:result.end]
                })
        else:
            # Fallback to regex
            for pii_type, pattern in self.pii_patterns.items():
                matches = pattern.finditer(text)
                for match in matches:
                    findings.append({
                        "type": pii_type,
                        "score": 0.9,
                        "text": match.group(0)
                    })
        
        return {
            "found": len(findings) > 0,
            "count": len(findings),
            "findings": findings
        }
    
    def scan_secrets(self, text: str) -> Dict[str, Any]:
        """Scan text for secrets."""
        findings = []
        
        for secret_type, pattern in self.secrets_patterns.items():
            matches = pattern.finditer(text)
            for match in matches:
                findings.append({
                    "type": secret_type,
                    "severity": "critical",
                    "text": match.group(0)[:20] + "..."  # Truncate for safety
                })
        
        return {
            "found": len(findings) > 0,
            "count": len(findings),
            "findings": findings
        }
    
    async def scan_mcp_endpoint(self, mcp_url: str) -> Dict[str, Any]:
        """Scan MCP endpoint for vulnerabilities."""
        findings = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
        }
        issues = []
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Test 1: Check if authentication required
                try:
                    response = await client.get(f"{mcp_url}/health")
                    if response.status_code == 200:
                        issues.append({
                            "severity": "low",
                            "title": "Health endpoint exposed",
                            "description": "Health endpoint accessible without authentication"
                        })
                        findings["low"] += 1
                except:
                    pass
                
                # Test 2: Check for rate limiting
                start = time.time()
                for _ in range(10):
                    try:
                        await client.get(mcp_url)
                    except:
                        pass
                elapsed = time.time() - start
                
                if elapsed < 1.0:  # 10 requests in < 1 second
                    issues.append({
                        "severity": "high",
                        "title": "Missing rate limiting",
                        "description": "No rate limiting detected - vulnerable to DoS"
                    })
                    findings["high"] += 1
                
                # Test 3: Check for error information disclosure
                try:
                    response = await client.get(f"{mcp_url}/nonexistent")
                    if "traceback" in response.text.lower() or "error" in response.text.lower():
                        issues.append({
                            "severity": "medium",
                            "title": "Information disclosure",
                            "description": "Error messages may leak sensitive information"
                        })
                        findings["medium"] += 1
                except:
                    pass
                
        except Exception as e:
            logger.error(f"Error scanning MCP endpoint: {e}")
        
        return {
            "findings": findings,
            "issues": issues
        }
    
    async def scan_mcp(self, mcp_name: str, mcp_url: str, test_prompts: List[str] = None) -> Dict[str, Any]:
        """Full MCP security scan."""
        start_time = time.time()
        
        logger.info(f"Starting PT scan for {mcp_name} at {mcp_url}")
        
        results = {
            "mcp_name": mcp_name,
            "mcp_url": mcp_url,
            "scan_depth": self.scan_depth,
            "timestamp": time.time(),
            "pii_findings": {"found": False, "count": 0},
            "secrets_findings": {"found": False, "count": 0},
            "security_findings": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "issues": [],
            "score": 100,
        }
        
        # Scan endpoint
        if self.tools.get("nuclei") or self.tools.get("semgrep"):
            endpoint_results = await self.scan_mcp_endpoint(mcp_url)
            results["security_findings"] = endpoint_results["findings"]
            results["issues"].extend(endpoint_results["issues"])
        
        # Test with prompts (if provided)
        if test_prompts:
            for prompt in test_prompts:
                # Check for PII in prompt
                if self.tools.get("presidio"):
                    pii_result = self.scan_pii(prompt)
                    if pii_result["found"]:
                        results["pii_findings"]["count"] += pii_result["count"]
                        results["pii_findings"]["found"] = True
                
                # Check for secrets
                if self.tools.get("truffleHog"):
                    secrets_result = self.scan_secrets(prompt)
                    if secrets_result["found"]:
                        results["secrets_findings"]["count"] += secrets_result["count"]
                        results["secrets_findings"]["found"] = True
        
        # Calculate score
        score = 100
        score -= results["security_findings"]["critical"] * 20
        score -= results["security_findings"]["high"] * 10
        score -= results["security_findings"]["medium"] * 5
        score -= results["security_findings"]["low"] * 2
        results["score"] = max(0, score)
        
        results["scan_duration_ms"] = int((time.time() - start_time) * 1000)
        
        logger.info(f"PT scan completed for {mcp_name} - Score: {results['score']}")
        
        return results
    
    def reload_config(self, new_config: Dict[str, Any]):
        """Reload configuration."""
        logger.info("Reloading MCP PT configuration", new_config=new_config)
        self.config = new_config
        self.enabled = new_config.get("enabled", True)
        self.tools = new_config.get("tools", {})
        self.scan_depth = new_config.get("scan_depth", "standard")
