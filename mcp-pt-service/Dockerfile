FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy and install dependencies
COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

# Copy source code
COPY *.py .
COPY routers/ ./routers/

# Expose port
EXPOSE 8200

# Run service
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8200"]
