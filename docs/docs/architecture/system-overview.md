---
sidebar_position: 2
---

# System Overview

## Architecture Layers

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
    Cloud Infrastructure (Docker → Kubernetes → Terraform)
```

## Service Domains

| Domain | Services | Phase | Description |
|--------|----------|-------|-------------|
| Gateway | 3 | 1 | API routing, GraphQL, BFF |
| Identity | 6 | 1 | Auth, sessions, OTP, SSO |
| User | 5 | 1 | Profiles, addresses, preferences |
| Config | 2 | 1 | Runtime config, feature flags |
| Driver | 8 | 2 | Driver lifecycle, location, ratings |
| Vehicle | 4 | 2 | Vehicle management, fleet |
| Mobility | 8 | 2 | Trips, dispatch, routing |
| Pricing | 6 | 2 | Fares, surge, promotions |
| Payment | 7 | 2 | Wallets, billing, payouts |
| Communication | 6 | 2 | Notifications, email, chat |
| Data Ingestion | 6 | 3 | Kafka consumers, CDC, batch |
| Stream Processing | 5 | 3 | Windowed aggregations |
| Analytics | 8 | 3 | Query APIs, reporting, cohorts |
| ML Feature | 5 | 4 | Feature store, pipelines |
| ML Training | 5 | 4 | Model training, tuning |
| ML Serving | 5 | 4 | Predictions, A/B testing |
| AI | 8 | 6 | ETA, fraud, chatbot, demand |
| Simulation | 4 | 7 | City, traffic, fleet simulators |

## Database Strategy

| Database | Role | Phase |
|----------|------|-------|
| PostgreSQL 16 | Primary OLTP, user data, transactions | 1+ |
| Redis 7 | Caching, sessions, real-time features | 1+ |
| ClickHouse | Analytics warehouse, OLAP queries | 3+ |
| MinIO | Object storage, data lake (S3-compatible) | 3+ |
| Elasticsearch | Full-text search, log aggregation | 6+ |
| ScyllaDB | High-throughput time-series (driver locations) | 7+ |
