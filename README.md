# Smart Mobility & Analytics Platform

A **2-year enterprise learning project** covering the full spectrum of modern engineering through a ride-hailing platform.

## What This Covers

| Discipline | Technologies | Phase |
|-----------|-------------|-------|
| **Backend Engineering** | FastAPI, Express, 155 microservices | 1-2 |
| **Frontend Engineering** | React, Next.js, Module Federation | 1-5 |
| **Data Engineering** | Kafka, ClickHouse, MinIO, ETL/ELT | 2-3 |
| **Data Analysis** | SQL analytics on 1B+ trips, dashboards | 3 |
| **Data Science** | Feature engineering, PyTorch, forecasting | 4, 6 |
| **ML Engineering** | Model training, serving, A/B testing | 4, 6 |
| **MLOps** | MLflow, drift monitoring, CI/CD for ML | 4-5 |
| **DevOps / Platform** | Kubernetes, Terraform, Prometheus | 5 |
| **AI / Advanced ML** | Graph NNs, RL, NLP, fraud detection | 6 |
| **Distributed Systems** | Multi-region, chaos engineering | 7 |

## Architecture

```
Micro-Frontends (React/Next.js)
        |
    API Gateway (TypeScript/Express)
        |
    155 Microservices (Python/FastAPI + TypeScript)
        |
    Kafka Event Streaming
        |
    Polyglot Databases
    (PostgreSQL | Redis | ClickHouse | MinIO | Elasticsearch | ScyllaDB)
        |
    Data Platform (ETL, Star Schema, Data Lake)
        |
    ML Platform (Feature Store, Training, Serving)
        |
    Cloud Infrastructure (Docker -> Kubernetes -> Terraform)
```

## Real Data at Scale

- **1.7B+ NYC taxi trips** (2009-2024) for realistic analytics and ML
- **NOAA weather data** for demand/ETA feature engineering
- **OpenStreetMap** road network for routing and graph ML
- **NYC 311 events** for event-driven demand modeling

## 7-Phase Roadmap (24 Months)

| Phase | Months | Theme | Services |
|-------|--------|-------|----------|
| 1 | 1-3 | Platform Foundation | 16 (gateway, auth, user) |
| 2 | 4-6 | Business Logic & Events | 49 (driver, trip, pricing) |
| 3 | 7-9 | Data Platform | 27 (streaming, warehouse, ETL) |
| 4 | 10-12 | ML Platform | 19 (features, training, serving) |
| 5 | 13-16 | Infrastructure & DevOps | 10 (K8s, CI/CD, observability) |
| 6 | 17-20 | Advanced AI | 15 (ETA, fraud, RL, chatbot) |
| 7 | 21-24 | Global Scale | 19 (multi-region, chaos, capstone) |

## Quick Start

```bash
# 1. Start Phase 1 infrastructure
cp .env.example .env
docker-compose up -d

# 2. Download sample data
python data/scripts/download_nyc_taxi.py --years 2023 --months 1

# 3. Run Phase 1 learning demos
python learning/phase_1/run_phase1.py

# 4. Run tests
python -m pytest learning/phase_1/tests/ -v
```

## Project Structure

```
EnterprisePlatform/
  learning/          # Simulation modules (pure Python, 42 modules)
  services/          # Real microservices (155 services)
  frontend/          # Micro-frontends (6 apps + shell)
  data/              # Datasets, seeds, download scripts
  infra/             # Kubernetes, Terraform, Helm
  docs/              # Docusaurus documentation site
```

See [LEARNING_PATH.md](LEARNING_PATH.md) for the detailed 24-month curriculum.
