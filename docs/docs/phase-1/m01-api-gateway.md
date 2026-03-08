---
sidebar_position: 3
---

# M01: API Gateway Patterns

Learn how API gateways route requests, enforce rate limits, handle versioning, and implement circuit breakers.

## Key Concepts

- **Request Routing** — Path-based and header-based routing to backend services
- **Rate Limiting** — Token bucket, sliding window, and fixed window algorithms
- **API Versioning** — URL path, header, and query parameter strategies
- **Circuit Breakers** — Fail-fast patterns to prevent cascade failures

## What You'll Build

A simulation of an API gateway that demonstrates:

1. How routing tables map URLs to backend services
2. Rate limiting with configurable strategies
3. Version negotiation between clients and services
4. Circuit breaker state machine (closed → open → half-open)

## Running the Module

```bash
python -m learning.phase_1.src.m01_api_gateway.demo
```

## Related Service

`services/gateway/api-gateway/` — The real TypeScript/Express API gateway service.
