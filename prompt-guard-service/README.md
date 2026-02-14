# Prompt Guard Service

Real-time prompt injection detection using **Llama-Prompt-Guard-2-86M**.

## Features

- ✅ **Fast Detection** - 20-30ms latency on CPU
- ✅ **Redis Pub/Sub** - Async communication with omni2
- ✅ **Database Config** - Dynamic configuration via `omni2_config` table
- ✅ **Behavioral Tracking** - Escalate actions for repeat offenders
- ✅ **In-Memory Cache** - Cache results for repeated prompts
- ✅ **No Exposed Ports** - Internal service only
- ✅ **Fail-Open** - Allows traffic if service is down

## Architecture

```
User Message → omni2 → Redis Pub/Sub → Prompt Guard → Redis Pub/Sub → omni2 → LLM
                            ↓
                    [Block/Warn/Allow]
```

## Configuration

Configuration is stored in `omni2.omni2_config` table with key `prompt_guard`:

```json
{
  "enabled": true,
  "threshold": 0.5,
  "cache_ttl_seconds": 3600,
  "behavioral_tracking": {
    "enabled": true,
    "warning_threshold": 3,
    "block_threshold": 5,
    "window_hours": 24
  },
  "actions": {
    "warn": true,
    "filter": false,
    "block": false
  }
}
```

### Configuration Options

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | bool | Enable/disable prompt guard |
| `threshold` | float | Detection threshold (0.0-1.0) |
| `cache_ttl_seconds` | int | Cache TTL for repeated prompts |
| `behavioral_tracking.enabled` | bool | Track user violations |
| `behavioral_tracking.warning_threshold` | int | Violations before warning |
| `behavioral_tracking.block_threshold` | int | Violations before blocking |
| `behavioral_tracking.window_hours` | int | Time window for counting violations |
| `actions.warn` | bool | Log warning but allow |
| `actions.filter` | bool | Sanitize message |
| `actions.block` | bool | Block message completely |

## Actions

| Action | Description |
|--------|-------------|
| `allow` | No injection detected, proceed normally |
| `warn` | Potential injection, log warning but allow |
| `filter` | Injection detected, sanitize message |
| `block` | High-confidence injection, block completely |

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
docker exec omni2-prompt-guard curl http://localhost:8100/health
```

### 4. View Logs

```bash
docker-compose logs -f prompt-guard
```

## Integration with omni2

The service is automatically integrated when Redis is enabled:

1. **Startup**: omni2 initializes `PromptGuardClient` on startup
2. **Check**: Before LLM processing, message is checked via Redis pub/sub
3. **Action**: Based on result, message is allowed/warned/filtered/blocked
4. **Logging**: All detections are logged to `prompt_injection_log` table

## Performance

- **Latency**: 20-30ms (CPU inference)
- **Cache Hit**: <5ms
- **Timeout**: 2s (fail-open if exceeded)
- **Memory**: ~500MB (model + runtime)
- **CPU**: 0.5-2.0 cores

## Monitoring

### Check Detection Logs

```sql
SELECT 
    user_id,
    COUNT(*) as violations,
    AVG(injection_score) as avg_score,
    MAX(detected_at) as last_violation
FROM omni2.prompt_injection_log
WHERE detected_at > NOW() - INTERVAL '24 hours'
GROUP BY user_id
ORDER BY violations DESC;
```

### Top Risky Users

```sql
SELECT 
    u.email,
    COUNT(*) as attempts,
    MAX(pil.injection_score) as max_score
FROM omni2.prompt_injection_log pil
JOIN auth_service.users u ON u.id = pil.user_id
WHERE pil.detected_at > NOW() - INTERVAL '7 days'
GROUP BY u.email
ORDER BY attempts DESC
LIMIT 10;
```

## API Endpoints (Internal Only)

- `GET /health` - Health check
- `GET /` - Service info

## Redis Channels

| Channel | Direction | Purpose |
|---------|-----------|---------|
| `prompt_guard_check` | omni2 → guard | Check request |
| `prompt_guard_response` | guard → omni2 | Check result |
| `prompt_guard_config_reload` | omni2 → guard | Reload config |

## Troubleshooting

### Service Not Starting

```bash
# Check logs
docker-compose logs prompt-guard

# Check Redis connection
docker exec omni2-prompt-guard redis-cli -h omni2-redis ping

# Check database connection
docker exec omni2-prompt-guard psql -h omni_pg_db -U omni -d omni -c "SELECT 1"
```

### Model Download Issues

The model (~350MB) is downloaded on first run. If download fails:

```bash
# Pre-download model
docker exec omni2-prompt-guard python -c "
from transformers import AutoTokenizer, AutoModelForSequenceClassification
AutoTokenizer.from_pretrained('meta-llama/Llama-Prompt-Guard-2-86M')
AutoModelForSequenceClassification.from_pretrained('meta-llama/Llama-Prompt-Guard-2-86M')
"
```

### High Latency

- Check CPU usage: `docker stats omni2-prompt-guard`
- Increase CPU limit in docker-compose.yml
- Verify cache is working (check logs for "Cache hit")

## Security Notes

- ✅ No exposed ports (internal only)
- ✅ Fail-open design (allows traffic on error)
- ✅ Non-root user in container
- ✅ Read-only model cache
- ✅ SQL injection protection (parameterized queries)

## Future Enhancements

- [ ] Multi-language support (translation layer)
- [ ] Custom patterns for domain-specific attacks
- [ ] Prometheus metrics export
- [ ] A/B testing framework
- [ ] Model fine-tuning on detected attacks
