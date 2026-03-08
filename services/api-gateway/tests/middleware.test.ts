/**
 * Unit tests for api-gateway middleware logic.
 *
 * These tests exercise the in-memory / pure-logic portions of the
 * rate limiter and circuit breaker without requiring Redis or live
 * backend services.
 */

import { localTokenBucket } from "../src/middleware/rateLimiter";
import {
  CircuitState,
  recordFailure,
  recordSuccess,
  getCircuitState,
  resetCircuit,
} from "../src/middleware/circuitBreaker";

// ---------------------------------------------------------------------------
// Rate Limiter (in-memory token bucket)
// ---------------------------------------------------------------------------
describe("localTokenBucket", () => {
  afterEach(() => {
    // The module-level Map retains state between tests when running in the
    // same process.  We work around this by using a unique IP per test.
  });

  it("allows requests up to the configured limit", () => {
    const ip = "10.0.0.1";
    // Default config: 100 tokens per window
    for (let i = 0; i < 100; i++) {
      const result = localTokenBucket(ip);
      expect(result.allowed).toBe(true);
    }
  });

  it("rejects requests once the bucket is drained", () => {
    const ip = "10.0.0.2";
    // Drain all tokens
    for (let i = 0; i < 100; i++) {
      localTokenBucket(ip);
    }

    const result = localTokenBucket(ip);
    expect(result.allowed).toBe(false);
    expect(result.remaining).toBe(0);
    expect(result.retryAfter).toBeGreaterThanOrEqual(1);
  });

  it("returns remaining count correctly", () => {
    const ip = "10.0.0.3";
    const first = localTokenBucket(ip);
    expect(first.remaining).toBe(99); // 100 - 1

    const second = localTokenBucket(ip);
    expect(second.remaining).toBe(98);
  });
});

// ---------------------------------------------------------------------------
// Circuit Breaker
// ---------------------------------------------------------------------------
describe("circuitBreaker", () => {
  const svc = "test-service";

  beforeEach(() => {
    resetCircuit(svc);
  });

  it("starts in CLOSED state", () => {
    const state = getCircuitState(svc);
    expect(state.state).toBe(CircuitState.CLOSED);
    expect(state.failureCount).toBe(0);
  });

  it("remains CLOSED when failures are below the threshold", () => {
    for (let i = 0; i < 4; i++) {
      recordFailure(svc);
    }
    const state = getCircuitState(svc);
    expect(state.state).toBe(CircuitState.CLOSED);
    expect(state.failureCount).toBe(4);
  });

  it("transitions to OPEN after reaching failure threshold (5)", () => {
    for (let i = 0; i < 5; i++) {
      recordFailure(svc);
    }
    const state = getCircuitState(svc);
    expect(state.state).toBe(CircuitState.OPEN);
  });

  it("records success and increments successCount in CLOSED state", () => {
    recordSuccess(svc);
    recordSuccess(svc);
    const state = getCircuitState(svc);
    expect(state.successCount).toBe(2);
    expect(state.state).toBe(CircuitState.CLOSED);
  });

  it("resets to CLOSED on success during HALF_OPEN state", () => {
    // Force into HALF_OPEN state
    const entry = getCircuitState(svc);
    entry.state = CircuitState.HALF_OPEN;

    recordSuccess(svc);

    const state = getCircuitState(svc);
    expect(state.state).toBe(CircuitState.CLOSED);
    expect(state.failureCount).toBe(0);
  });

  it("re-opens on failure during HALF_OPEN state", () => {
    const entry = getCircuitState(svc);
    entry.state = CircuitState.HALF_OPEN;

    recordFailure(svc);

    const state = getCircuitState(svc);
    expect(state.state).toBe(CircuitState.OPEN);
  });

  it("resetCircuit clears all state", () => {
    for (let i = 0; i < 5; i++) {
      recordFailure(svc);
    }
    expect(getCircuitState(svc).state).toBe(CircuitState.OPEN);

    resetCircuit(svc);
    const state = getCircuitState(svc);
    expect(state.state).toBe(CircuitState.CLOSED);
    expect(state.failureCount).toBe(0);
  });
});
