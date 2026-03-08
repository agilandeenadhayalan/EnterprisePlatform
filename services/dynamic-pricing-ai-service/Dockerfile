FROM python:3.12-slim AS base
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*
COPY services/shared/python/mobility-common/ /app/mobility-common/
RUN pip install --no-cache-dir /app/mobility-common/
COPY services/dynamic-pricing-ai-service/pyproject.toml /app/service/
RUN pip install --no-cache-dir /app/service/
COPY services/dynamic-pricing-ai-service/src/ /app/service/src/
WORKDIR /app/service/src
EXPOSE 8075
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8075/health')" || exit 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8075"]
