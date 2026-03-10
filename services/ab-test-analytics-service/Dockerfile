FROM python:3.11-slim
WORKDIR /app
COPY . /app/services/ab-test-analytics-service/
COPY ../shared /app/services/shared/
RUN pip install --no-cache-dir -e /app/services/shared/python/mobility-common
RUN pip install --no-cache-dir fastapi uvicorn[standard] pydantic pydantic-settings httpx redis sqlalchemy asyncpg aiokafka clickhouse-connect minio pyarrow numpy scipy mlflow-skinny
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
WORKDIR /app/services/ab-test-analytics-service/src
