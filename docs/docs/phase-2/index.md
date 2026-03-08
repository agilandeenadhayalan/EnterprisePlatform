---
sidebar_position: 1
---

# Phase 2: Business Logic & Events

**Months 4-6** — Core domain: drivers, trips, dispatch, pricing, payments, real-time.

## Learning Modules

| Module | Topic | Key Concepts |
|--------|-------|-------------|
| M07 | Domain-Driven Design | Bounded contexts, aggregates, event storming |
| M08 | Event-Driven Architecture | Kafka, event sourcing, CQRS, saga |
| M09 | Dispatch Algorithms | Nearest-driver, scoring, Hungarian algorithm |
| M10 | Dynamic Pricing | Surge pricing, supply/demand, price elasticity |
| M11 | Real-Time Communication | WebSocket, pub/sub, presence, backpressure |
| M12 | Geospatial Computing | Haversine, H3 grids, geohash, PostGIS |

## Services Built: 49

Driver (8) + Vehicle (4) + Mobility (8) + Pricing (6) + Payment (7) + Communication (6) + Real-Time (3) + Search (3) + Marketplace (4)

## Infrastructure Added

Kafka (KRaft mode), Schema Registry, Kafka UI

## Data

NYC taxi 2023 (~37M trips) replayed as Kafka events
