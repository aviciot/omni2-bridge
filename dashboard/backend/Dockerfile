FROM python:3.11-slim

RUN pip install uv

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app

RUN uv pip install --system -e .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8500", "--reload"]
