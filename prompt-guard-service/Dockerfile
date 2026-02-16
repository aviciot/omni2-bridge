# ============================================================
# Prompt Guard Service Dockerfile
# ============================================================
# Lightweight prompt injection detection using Llama-Prompt-Guard-2-86M
# ============================================================

FROM python:3.11-slim as base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ============================================================
# Install dependencies using pip (simpler than uv)
# ============================================================
COPY pyproject.toml ./

# Install PyTorch CPU-only (smaller)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install other dependencies
RUN pip install --no-cache-dir \
    fastapi>=0.104.0 \
    uvicorn[standard]>=0.24.0 \
    redis>=5.0.0 \
    transformers>=4.35.0 \
    pydantic>=2.5.0 \
    pydantic-settings>=2.1.0 \
    asyncpg>=0.29.0 \
    sqlalchemy>=2.0.23 \
    structlog>=23.2.0 \
    orjson>=3.9.10 \
    protobuf>=4.25.0

# ============================================================
# Copy application code
# ============================================================
COPY . .

# Create non-root user
RUN useradd -m -u 1000 guarduser && \
    mkdir -p /app/logs /app/models && \
    chown -R guarduser:guarduser /app

USER guarduser

# Pre-download model during build (speeds up first run)
RUN python -c "from transformers import AutoTokenizer, AutoModelForSequenceClassification; \
    AutoTokenizer.from_pretrained('ProtectAI/deberta-v3-base-prompt-injection-v2'); \
    AutoModelForSequenceClassification.from_pretrained('ProtectAI/deberta-v3-base-prompt-injection-v2')"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8100/health', timeout=5)"

# Start service
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8100"]
