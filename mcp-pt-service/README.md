# MCP PT Service

Penetration Testing service for MCP servers with PII/Secrets detection.

## Features

- ✅ **PII Detection** - Microsoft Presidio (ML-based)
- ✅ **Secrets Detection** - TruffleHog patterns
- ✅ **Security Testing** - Rate limiting, auth, error disclosure
- ✅ **Redis Pub/Sub** - Async communication with omni2
- ✅ **Database Config** - Dynamic configuration via UI
- ✅ **Scoring System** - 0-100 security score

## Architecture

```
UI → omni2 → Redis Pub/Sub → MCP PT Service → Scan Results → Database
```

## Configuration

Configuration stored in `omni2.omni2_config` table with key `mcp_pt`:

```json
{
  "enabled": true,
  "tools": {
    "presidio": true,
    "truffleHog": true,
    "nuclei": false,
    "semgrep": false
  },
  "scan_depth": "standard",
  "auto_scan": false,
  "schedule_cron": "0 2 * * *"
}
```

## Deployment

### 1. Apply Database Schema

```bash
psql -h localhost -U omni -d omni -f schema.sql
```

### 2. Start Service

```bash
docker-compose up -d
```

### 3. Check Health

```bash
curl http://localhost:8200/health
```

## Redis Channels

| Channel | Direction | Purpose |
|---------|-----------|---------|
| `mcp_pt_scan` | omni2 → pt | Scan request |
| `mcp_pt_response` | pt → omni2 | Scan result |
| `mcp_pt_config_reload` | omni2 → pt | Reload config |

## Scan Request Format

```json
{
  "scan_id": "uuid",
  "mcp_name": "filesystem-mcp",
  "mcp_url": "http://mcp:8080",
  "test_prompts": ["test prompt 1", "test prompt 2"]
}
```

## Scan Result Format

```json
{
  "mcp_name": "filesystem-mcp",
  "mcp_url": "http://mcp:8080",
  "score": 85,
  "pii_findings": {
    "found": true,
    "count": 2
  },
  "secrets_findings": {
    "found": false,
    "count": 0
  },
  "security_findings": {
    "critical": 0,
    "high": 1,
    "medium": 3,
    "low": 5
  },
  "issues": [
    {
      "severity": "high",
      "title": "Missing rate limiting",
      "description": "No rate limiting detected"
    }
  ]
}
```

## Tools

### Presidio (PII Detection)
- Credit cards
- SSN
- Emails
- Phone numbers
- ML-based entity recognition

### TruffleHog (Secrets Detection)
- AWS keys
- GitHub tokens
- API keys
- Passwords

### Security Tests
- Authentication check
- Rate limiting
- Error disclosure
- Information leakage

## Development

```bash
# Install with uv
uv pip install -e .

# Run locally
uvicorn main:app --reload --port 8200
```
