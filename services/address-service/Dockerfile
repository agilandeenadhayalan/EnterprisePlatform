# ──────────────────────────────────────────────
# Address Service — Multi-stage Docker build
# ──────────────────────────────────────────────
# Stage 1: Install dependencies (cached layer)
# Stage 2: Copy source code (changes frequently)

FROM python:3.12-slim AS base

WORKDIR /app

# Install system dependencies for asyncpg (PostgreSQL client)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy shared library first (changes less frequently)
COPY services/shared/python/mobility-common/ /app/mobility-common/
RUN pip install --no-cache-dir /app/mobility-common/

# Copy service dependencies
COPY services/address-service/pyproject.toml /app/service/
RUN pip install --no-cache-dir /app/service/

# Copy service source code (changes most frequently → last layer)
COPY services/address-service/src/ /app/service/src/

WORKDIR /app/service/src

EXPOSE 8022

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8022/health')" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8022"]
