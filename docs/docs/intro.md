---
sidebar_position: 1
slug: /intro
---

# Smart Mobility & Analytics Platform

A **2-year enterprise learning project** covering the full spectrum of modern engineering through a ride-hailing platform.

## What You'll Build

A complete Uber-like platform with **155 microservices**, trained on **1.7 billion real NYC taxi trips**, spanning:

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

## Learning Approach

Each phase follows a **hybrid model**:

1. **Learning modules** — Pure Python simulations teaching concepts
2. **Real services** — Actual microservices with APIs, databases, and event streams

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

## Project Scale

| Metric | Count |
|--------|-------|
| Learning Modules | 42 |
| Microservices | 155 |
| Frontend Apps | 7 |
| Exercises | 46 |
| Kafka Topics | ~43 |
| Database Tables | ~90+ |
| Real Data | 1.7B+ trips |
| Databases | 6 types |
