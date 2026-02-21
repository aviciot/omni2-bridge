# MCP PT Service - Implementation Complete

## 📁 Structure

```
omni2/
├── mcp-pt-service/              # New PT service
│   ├── config.py                # Environment settings
│   ├── logger.py                # Structured logging
│   ├── db.py                    # Database operations
│   ├── scanner.py               # PII/Secrets/PT scanner
│   ├── redis_handler.py         # Pub/sub communication
│   ├── main.py                  # FastAPI application
│   ├── schema.sql               # Database schema
│   ├── pyproject.toml           # uv dependencies
│   ├── Dockerfile               # Container image
│   ├── docker-compose.yml       # Deployment config
│   └── README.md                # Documentation
│
└── app/routers/
    └── mcp_pt_admin.py          # Admin API for UI
```

## 🎯 Features Implemented

### 1. PII Detection (Microsoft Presidio)
- Credit cards
- SSN
- Emails
- Phone numbers
- ML-based entity recognition
- Fallback to regex if Presidio unavailable

### 2. Secrets Detection (TruffleHog patterns)
- AWS keys (AKIA...)
- GitHub tokens (ghp_...)
- API keys (sk-...)
- Passwords in plain text

### 3. Security Testing
- Authentication check
- Rate limiting detection
- Error information disclosure
- Health endpoint exposure

### 4. Scoring System
- 100 = Perfect security
- -20 per critical issue
- -10 per high issue
- -5 per medium issue
- -2 per low issue

## 🔧 Configuration

Stored in `omni2.omni2_config` table:

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

## 📡 Communication Flow

```
UI → omni2 API → Redis Pub/Sub → MCP PT Service → Scan → Database
                                                    ↓
                                            Redis Response → UI
```

### Redis Channels:
- `mcp_pt_scan` - Scan requests (omni2 → pt)
- `mcp_pt_response` - Scan results (pt → omni2)
- `mcp_pt_config_reload` - Config updates (omni2 → pt)

## 🚀 Deployment

### 1. Apply Database Schema

```bash
cd omni2/mcp-pt-service
psql -h localhost -U omni -d omni -f schema.sql
```

### 2. Start Service

```bash
docker-compose up -d
```

### 3. Verify

```bash
curl http://localhost:8200/health
```

## 📊 API Endpoints (omni2)

### Get Configuration
```
GET /api/v1/mcp-pt/config
```

### Update Configuration
```
PUT /api/v1/mcp-pt/config
Body: {
  "enabled": true,
  "tools": {"presidio": true, "truffleHog": true},
  "scan_depth": "standard"
}
```

### Start Scan
```
POST /api/v1/mcp-pt/scan
Body: {
  "mcp_names": ["filesystem-mcp", "github-mcp"],
  "test_prompts": ["test prompt 1"]
}
```

### Get Scan Results
```
GET /api/v1/mcp-pt/scans?limit=50&mcp_name=filesystem-mcp
```

### Get Scan Detail
```
GET /api/v1/mcp-pt/scans/{scan_id}
```

### Get Available MCPs
```
GET /api/v1/mcp-pt/mcps
```

## 📈 Scan Result Format

```json
{
  "mcp_name": "filesystem-mcp",
  "mcp_url": "http://mcp:8080",
  "score": 85,
  "pii_findings": {
    "found": true,
    "count": 2,
    "findings": [
      {
        "type": "CREDIT_CARD",
        "score": 0.95,
        "text": "4532-1234-5678-9010"
      }
    ]
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
      "description": "No rate limiting detected - vulnerable to DoS"
    }
  ],
  "scan_duration_ms": 1234
}
```

## 🎨 Next Steps: UI Implementation

### Create Dashboard Tab

**Location:** `dashboard/frontend/src/app/admin/security/mcp-pt/page.tsx`

**Features:**
1. List available MCPs with checkboxes
2. Tool selection (Presidio, TruffleHog, etc.)
3. Scan depth selector (Quick/Standard/Deep)
4. Start scan button
5. Results table with scores
6. Detailed view with graphs
7. Export report (PDF/JSON)

**Components needed:**
- `MCPPTSettings.tsx` - Configuration panel
- `MCPPTScanner.tsx` - Scan interface
- `MCPPTResults.tsx` - Results viewer
- `MCPPTChart.tsx` - Score visualization

## 🔐 Security Notes

- Service runs on internal network only (no exposed ports)
- Uses same database/Redis as omni2
- Fail-safe design (errors don't block scans)
- All secrets truncated in logs
- PII anonymization available via Presidio

## 📝 TODO

- [ ] Add Nuclei integration (CVE scanning)
- [ ] Add Semgrep integration (code analysis)
- [ ] Implement scheduled scans (cron)
- [ ] Add email notifications for critical findings
- [ ] Create PDF report generator
- [ ] Add historical trend analysis
- [ ] Implement auto-remediation suggestions

## 🧪 Testing

```bash
# Test PII detection
curl -X POST http://localhost:8200/test/pii \
  -H "Content-Type: application/json" \
  -d '{"text": "My credit card is 4532-1234-5678-9010"}'

# Test secrets detection
curl -X POST http://localhost:8200/test/secrets \
  -H "Content-Type: application/json" \
  -d '{"text": "AWS_KEY=AKIA1234567890ABCDEF"}'
```

## 📚 Dependencies

- **Presidio** - Microsoft's PII detection (ML-based)
- **TruffleHog** - Secrets scanning
- **httpx** - HTTP client for endpoint testing
- **FastAPI** - Web framework
- **Redis** - Pub/sub communication
- **PostgreSQL** - Results storage

All managed via `uv` package manager.
