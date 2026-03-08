---
sidebar_position: 2
---

# Getting Started with Phase 1

## Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Node.js 18+ (for API Gateway)

## Start Infrastructure

```bash
# From project root
cp .env.example .env
docker-compose up -d
```

This starts:
- **PostgreSQL** on port 5433 (auto-creates schemas and tables)
- **Redis** on port 6380
- **pgAdmin** on port 5050 (admin@mobility.dev / admin123)

## Verify Setup

```bash
# Check containers are healthy
docker-compose ps

# Connect to PostgreSQL
docker exec -it mobility-postgres psql -U mobility_admin -d mobility_platform

# Check schemas
\dn
# Should show: identity, users, platform

# Check tables
\dt identity.*
# Should show: users, user_sessions, api_keys
```

## Run Learning Modules

```bash
# Run all Phase 1 demos
python learning/phase_1/run_phase1.py

# Run specific module
python -m learning.phase_1.src.m01_api_gateway.demo

# Run tests
python -m pytest learning/phase_1/tests/ -v

# Try exercises (they start as NotImplementedError)
python -m pytest learning/phase_1/exercises/ -v
```

## Directory Structure

```
learning/phase_1/
  run_phase1.py              # Run all demos
  pyproject.toml             # Phase config
  src/
    m01_api_gateway/         # Module 1: API Gateway Patterns
    m02_authentication/      # Module 2: Auth & Authorization
    m03_rest_api_design/     # Module 3: RESTful API Design
    m04_database_patterns/   # Module 4: Database Connection Patterns
    m05_caching/             # Module 5: Caching Strategies
    m06_containerization/    # Module 6: Containerization
  tests/
    conftest.py              # Shared fixtures
    test_m01.py - test_m06.py
  exercises/
    ex1_rate_limiter.py - ex7_circuit_breaker.py
```
