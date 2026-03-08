---
sidebar_position: 2
---

# Getting Started with Phase 2

*Coming in Months 4-6 — requires Phase 1 completion.*

## Prerequisites

- All Phase 1 services running
- NYC taxi data downloaded (`python data/scripts/download_nyc_taxi.py --years 2023`)

## Infrastructure

```bash
docker-compose -f docker-compose.yml -f docker-compose.phase2.yml up -d
```
