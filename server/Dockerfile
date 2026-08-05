FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_SYSTEM_PYTHON=1

WORKDIR /app

# Copy dependency manifests first (layer cache)
COPY requirements.txt ./

RUN uv pip install --no-cache -r requirements.txt

COPY . .

# Mount points created here; volumes/bind-mounts will override at runtime
RUN mkdir -p /data /models

EXPOSE 8000

# Single worker required — APScheduler background tasks break with multiple workers
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
