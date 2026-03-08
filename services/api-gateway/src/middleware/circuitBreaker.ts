import { Request, Response, NextFunction } from "express";
import { config } from "../config";

/**
 * Circuit breaker states.
 *
 *  CLOSED     — traffic flows normally; failures are counted.
 *  OPEN       — all requests are immediately rejected with 503.
 *  HALF_OPEN  — a single probe request is allowed through to test recovery.
 */
export enum CircuitState {
  CLOSED = "CLOSED",
  OPEN = "OPEN",
  HALF_OPEN = "HALF_OPEN",
}

export interface CircuitBreakerEntry {
  state: CircuitState;
  failureCount: number;
  lastFailureTime: number;
  successCount: number;
}

/**
 * Per-service circuit breaker map.
 * Key = service name (derived from the route prefix).
 */
const circuits = new Map<string, CircuitBreakerEntry>();

function getOrCreate(serviceName: string): CircuitBreakerEntry {
  let entry = circuits.get(serviceName);
  if (!entry) {
    entry = {
      state: CircuitState.CLOSED,
      failureCount: 0,
      lastFailureTime: 0,
      successCount: 0,
    };
    circuits.set(serviceName, entry);
  }
  return entry;
}

/**
 * Record a successful response from a backend service.
 */
export function recordSuccess(serviceName: string): void {
  const entry = getOrCreate(serviceName);

  if (entry.state === CircuitState.HALF_OPEN) {
    // Successful probe — close the circuit
    entry.state = CircuitState.CLOSED;
    entry.failureCount = 0;
    entry.successCount = 0;
    console.log(`[CircuitBreaker] ${serviceName}: HALF_OPEN -> CLOSED`);
  }

  entry.successCount += 1;
}

/**
 * Record a failed response / connection error from a backend service.
 */
export function recordFailure(serviceName: string): void {
  const entry = getOrCreate(serviceName);
  entry.failureCount += 1;
  entry.lastFailureTime = Date.now();

  if (entry.state === CircuitState.HALF_OPEN) {
    // Probe failed — reopen the circuit
    entry.state = CircuitState.OPEN;
    console.log(`[CircuitBreaker] ${serviceName}: HALF_OPEN -> OPEN`);
    return;
  }

  if (
    entry.state === CircuitState.CLOSED &&
    entry.failureCount >= config.circuitBreaker.failureThreshold
  ) {
    entry.state = CircuitState.OPEN;
    console.log(
      `[CircuitBreaker] ${serviceName}: CLOSED -> OPEN (${entry.failureCount} failures)`
    );
  }
}

/**
 * Get the current state of a service's circuit.
 */
export function getCircuitState(serviceName: string): CircuitBreakerEntry {
  return getOrCreate(serviceName);
}

/**
 * Reset a circuit (useful for testing or admin endpoints).
 */
export function resetCircuit(serviceName: string): void {
  circuits.delete(serviceName);
}

/**
 * Express middleware that checks the circuit breaker BEFORE the request
 * is forwarded to the proxy.
 *
 * The `serviceName` is extracted from the first segment of the route path,
 * e.g. `/api/v1/users/123` => `users`.
 */
export function circuitBreakerMiddleware() {
  return (req: Request, res: Response, next: NextFunction) => {
    // Derive service name from path: /api/v1/<service>/...
    const parts = req.path.split("/").filter(Boolean);
    // parts = ["api", "v1", "<service>", ...]
    const serviceName = parts.length >= 3 ? parts[2] : "unknown";

    const entry = getOrCreate(serviceName);

    // Transition from OPEN to HALF_OPEN if enough time has passed
    if (entry.state === CircuitState.OPEN) {
      const elapsed = Date.now() - entry.lastFailureTime;
      if (elapsed >= config.circuitBreaker.resetTimeoutMs) {
        entry.state = CircuitState.HALF_OPEN;
        console.log(`[CircuitBreaker] ${serviceName}: OPEN -> HALF_OPEN`);
      } else {
        res.status(503).json({
          error: "Service Unavailable",
          message: `Circuit breaker is OPEN for service '${serviceName}'. Try again later.`,
        });
        return;
      }
    }

    next();
  };
}
