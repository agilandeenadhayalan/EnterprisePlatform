# Smart Mobility & Analytics Platform — Learning Path

## 24-Month Curriculum (7 Phases, 42 Modules, 155 Services)

Each phase follows a **hybrid approach**:
1. **Learning modules** — Pure Python simulations teaching concepts (like DataEng)
2. **Real services** — Actual microservices with APIs, databases, and event streams

---

## Phase 1: Platform Foundation (Months 1-3)

> Build the skeleton: users, auth, API gateway, admin dashboard.

| Module | Topic | Key Concepts |
|--------|-------|-------------|
| M01 | API Gateway Patterns | Routing, rate limiting, versioning, circuit breakers |
| M02 | Authentication & Authorization | JWT, OAuth2, RBAC, token rotation |
| M03 | RESTful API Design | Richardson Maturity, pagination, idempotency |
| M04 | Database Connection Patterns | Pooling, Repository pattern, N+1 queries |
| M05 | Caching Strategies | Cache-aside, write-through, stampede prevention |
| M06 | Containerization | Multi-stage Dockerfile, compose, healthchecks |

**Services**: 16 (api-gateway, auth, user, session, config...)
**Frontend**: admin-dashboard
**Infra**: PostgreSQL, Redis
**Exercises**: 7

---

## Phase 2: Business Logic & Events (Months 4-6)

> Core domain: drivers, trips, dispatch, pricing, payments, real-time.

| Module | Topic | Key Concepts |
|--------|-------|-------------|
| M07 | Domain-Driven Design | Bounded contexts, aggregates, event storming |
| M08 | Event-Driven Architecture | Kafka, event sourcing, CQRS, saga |
| M09 | Dispatch Algorithms | Nearest-driver, scoring, Hungarian algorithm |
| M10 | Dynamic Pricing | Surge pricing, supply/demand, price elasticity |
| M11 | Real-Time Communication | WebSocket, pub/sub, presence, backpressure |
| M12 | Geospatial Computing | Haversine, H3 grids, geohash, PostGIS |

**Services**: 49 (driver, vehicle, trip, dispatch, pricing, payment, chat...)
**Frontend**: rider-app, driver-app
**Infra**: + Kafka, Schema Registry
**Data**: NYC taxi 2023 (~37M trips) replayed as Kafka events
**Exercises**: 7

---

## Phase 3: Data Platform (Months 7-9)

> Analytics backbone: streaming pipelines, ClickHouse, data lake, dashboards.

| Module | Topic | Key Concepts |
|--------|-------|-------------|
| M13 | Streaming Pipeline Design | Consumer groups, windowing, exactly-once |
| M14 | Analytics Warehouse Design | Star schema, MergeTree, materialized views |
| M15 | Data Lake Architecture | Medallion (Bronze/Silver/Gold), Parquet |
| M16 | ETL/ELT Pipeline Patterns | DAG-based, incremental, CDC, SCD Type 2 |
| M17 | Data Quality Framework | Profiling, rule engines, anomaly detection |
| M18 | Query Optimization | ClickHouse plans, skip indexes, partitions |

**Services**: 27 (stream processors, analytics, ETL workers, data lake...)
**Frontend**: analytics-dashboard
**Infra**: + ClickHouse, MinIO
**Data**: ALL NYC taxi (2009-2024, 1.7B+ rows) + NOAA weather
**Exercises**: 6

---

## Phase 4: ML Platform (Months 10-12)

> ML infrastructure: feature store, training, serving, monitoring.

| Module | Topic | Key Concepts |
|--------|-------|-------------|
| M19 | Feature Engineering | Online/offline features, point-in-time |
| M20 | Model Training Pipelines | PyTorch, hyperparameter tuning, MLflow |
| M21 | Model Serving Patterns | REST inference, batching, A/B, shadow |
| M22 | ML Monitoring | Data drift (PSI), concept drift, retraining |
| M23 | Recommendation Systems | Collaborative/content-based, cold start |
| M24 | Time Series Forecasting | ARIMA, decomposition, uncertainty |

**Services**: 19 (feature store, training, prediction, monitoring...)
**Frontend**: ml-workbench
**Infra**: + MLflow
**Data**: Train on 1B+ real trips + weather features
**Exercises**: 6

---

## Phase 5: Infrastructure & DevOps (Months 13-16)

> Production: Kubernetes, CI/CD, observability, SLO tracking.

| Module | Topic | Key Concepts |
|--------|-------|-------------|
| M25 | Kubernetes Fundamentals | Pods, Deployments, Services, Ingress |
| M26 | Helm & Kustomize | Charts, overlays, environment promotion |
| M27 | CI/CD Pipeline Design | GitHub Actions, blue-green, canary |
| M28 | Observability Stack | Prometheus, Grafana, Jaeger, Loki |
| M29 | Service Mesh Basics | Sidecar proxy, mTLS, traffic splitting |
| M30 | Infrastructure as Code | Terraform, state, modules, plan/apply |

**Services**: 10 (deployment, health, SLO tracker, alerting...)
**Frontend**: ops-dashboard
**Infra**: + Prometheus, Grafana, Jaeger, K8s
**Exercises**: 7

---

## Phase 6: Advanced AI (Months 17-20)

> Advanced ML: deep ETA, demand forecast, fraud, NLP chatbot, RL dispatch.

| Module | Topic | Key Concepts |
|--------|-------|-------------|
| M31 | ETA Prediction | Graph neural networks, road network features |
| M32 | Demand Forecasting | Spatio-temporal, weather, uncertainty |
| M33 | Fraud Detection | Anomaly detection, graph analysis |
| M34 | NLP & Chatbot | Intent classification, NER, RAG |
| M35 | Experimentation | A/B testing, multi-armed bandit |
| M36 | Reinforcement Learning | MDP, Q-learning, multi-agent RL |

**Services**: 15 (ETA, demand, fraud, chatbot, RL dispatch...)
**Frontend**: ml-workbench extensions
**Infra**: + Elasticsearch
**Data**: Train on OSM road network + real taxi GPS traces
**Exercises**: 6

---

## Phase 7: Global Scale (Months 21-24)

> Scale: multi-region, chaos, performance, cost optimization, capstone.

| Module | Topic | Key Concepts |
|--------|-------|-------------|
| M37 | Multi-Region Architecture | Active-active, CRDTs, geo-routing |
| M38 | Chaos Engineering | Failure injection, hypothesis testing |
| M39 | Performance Testing | k6, p99 latency, queuing theory |
| M40 | Cost Optimization | Right-sizing, unit economics |
| M41 | Data Governance | Lineage, PII detection, GDPR |
| M42 | City Simulation (Capstone) | Agent-based modeling, full integration |

**Services**: 19 (region router, chaos, simulator, compliance...)
**Frontend**: ops-dashboard extensions
**Infra**: + ScyllaDB, k6, Toxiproxy
**Data**: Multi-city (NYC + Chicago), 1B+ events load test
**Exercises**: 7

---

## Total Project Scale

| Metric | Count |
|--------|-------|
| Learning Modules | 42 |
| Microservices | 155 |
| Frontend Apps | 7 |
| Exercises | 46 |
| Kafka Topics | ~43 |
| Database Tables | ~90+ |
| Real Data | 1.7B+ trips |
| Databases | 6 (PostgreSQL, Redis, ClickHouse, MinIO, Elasticsearch, ScyllaDB) |
