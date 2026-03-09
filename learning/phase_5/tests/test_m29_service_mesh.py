"""
Tests for M29: Service Mesh Basics — Sidecar proxies, traffic routing,
circuit breakers, and mutual TLS.
"""

import time
import pytest

from m29_service_mesh.sidecar_proxy import ProxyConfig, Request, Response, SidecarProxy
from m29_service_mesh.traffic_routing import TrafficRule, WeightedRouter, HeaderBasedRouter
from m29_service_mesh.circuit_breaker import CircuitBreakerState, CircuitBreaker, CircuitOpenError
from m29_service_mesh.mtls import Certificate, CertificateChain, MtlsHandshake, CertificateRotation


# ── SidecarProxy ──


class TestSidecarProxy:
    def test_inject_adds_container(self):
        """Sidecar injection adds a proxy container to the pod."""
        config = ProxyConfig(listen_port=15006, upstream_port=8080)
        proxy = SidecarProxy(config)
        containers = [{"name": "app", "image": "myapp:1.0"}]
        result = proxy.inject(containers)
        assert len(result) == 2
        assert result[1]["name"] == "istio-proxy"

    def test_inject_preserves_original(self):
        """Sidecar injection does not modify the original container list."""
        config = ProxyConfig(listen_port=15006, upstream_port=8080)
        proxy = SidecarProxy(config)
        containers = [{"name": "app", "image": "myapp:1.0"}]
        proxy.inject(containers)
        assert len(containers) == 1

    def test_handle_request_returns_response(self):
        """Proxy returns a 200 response for handled requests."""
        config = ProxyConfig(listen_port=15006, upstream_port=8080)
        proxy = SidecarProxy(config)
        req = Request("GET", "/api/users")
        resp = proxy.handle_request(req)
        assert resp.status_code == 200

    def test_handle_request_adds_headers(self):
        """Proxy adds x-request-id and x-proxy-id headers."""
        config = ProxyConfig(listen_port=15006, upstream_port=8080)
        proxy = SidecarProxy(config)
        req = Request("GET", "/api/users")
        resp = proxy.handle_request(req)
        assert "x-request-id" in resp.headers
        assert "x-proxy-id" in resp.headers
        assert resp.headers["x-proxy-id"] == "sidecar-15006"

    def test_metrics_tracking(self):
        """Proxy tracks request count and latency."""
        config = ProxyConfig(listen_port=15006, upstream_port=8080)
        proxy = SidecarProxy(config)
        proxy.handle_request(Request("GET", "/api/a"))
        proxy.handle_request(Request("POST", "/api/b"))
        metrics = proxy.get_metrics()
        assert metrics["requests"] == 2
        assert metrics["errors"] == 0
        assert metrics["success_rate"] == 1.0
        assert metrics["avg_latency_ms"] > 0

    def test_error_counting(self):
        """Proxy tracks error count and adjusts success rate."""
        config = ProxyConfig(listen_port=15006, upstream_port=8080)
        proxy = SidecarProxy(config)
        proxy.handle_request(Request("GET", "/api/a"))
        proxy.handle_request(Request("GET", "/api/b"))
        proxy.record_error()
        metrics = proxy.get_metrics()
        assert metrics["requests"] == 2
        assert metrics["errors"] == 1
        assert metrics["success_rate"] == 0.5


# ── WeightedRouter ──


class TestWeightedRouter:
    def test_add_rules(self):
        """Rules can be added to the router."""
        router = WeightedRouter()
        router.add_rule(TrafficRule("v1", 90))
        router.add_rule(TrafficRule("v2", 10))
        assert len(router.rules) == 2

    def test_validate_sum_100(self):
        """Validation passes when weights sum to 100."""
        router = WeightedRouter()
        router.add_rule(TrafficRule("v1", 90))
        router.add_rule(TrafficRule("v2", 10))
        assert router.validate() is True

    def test_validate_sum_wrong(self):
        """Validation fails when weights don't sum to 100."""
        router = WeightedRouter()
        router.add_rule(TrafficRule("v1", 50))
        router.add_rule(TrafficRule("v2", 30))
        assert router.validate() is False

    def test_deterministic_routing(self):
        """Same request_id always routes to the same destination."""
        router = WeightedRouter()
        router.add_rule(TrafficRule("v1", 90))
        router.add_rule(TrafficRule("v2", 10))
        dest1 = router.route("request-42")
        dest2 = router.route("request-42")
        assert dest1 == dest2

    def test_traffic_distribution(self):
        """Traffic distribution roughly matches configured weights."""
        router = WeightedRouter()
        router.add_rule(TrafficRule("v1", 90))
        router.add_rule(TrafficRule("v2", 10))
        dist = router.get_traffic_distribution(1000)
        # With 1000 requests, v1 should get ~900 and v2 ~100
        assert dist["v1"] > 700  # generous tolerance for hash distribution
        assert dist["v2"] > 0


# ── HeaderBasedRouter ──


class TestHeaderBasedRouter:
    def test_match_headers(self):
        """Request with matching headers routes to the correct destination."""
        rules = [
            TrafficRule("canary-v2", match_headers={"x-canary": "true"}),
            TrafficRule("stable-v1"),
        ]
        router = HeaderBasedRouter(rules=rules, default_destination="stable-v1")
        dest = router.route({"x-canary": "true", "accept": "application/json"})
        assert dest == "canary-v2"

    def test_no_match_default(self):
        """Request without matching headers routes to default."""
        rules = [
            TrafficRule("canary-v2", match_headers={"x-canary": "true"}),
        ]
        router = HeaderBasedRouter(rules=rules, default_destination="stable-v1")
        dest = router.route({"accept": "application/json"})
        assert dest == "stable-v1"

    def test_partial_match_fails(self):
        """Partial header matches do not trigger the rule."""
        rules = [
            TrafficRule("internal", match_headers={"x-internal": "true", "x-team": "platform"}),
        ]
        router = HeaderBasedRouter(rules=rules, default_destination="public")
        # Only one of two required headers present
        dest = router.route({"x-internal": "true"})
        assert dest == "public"


# ── CircuitBreaker ──


class TestCircuitBreaker:
    def test_closed_success(self):
        """Successful calls pass through in CLOSED state."""
        cb = CircuitBreaker(failure_threshold=3)
        result = cb.call(lambda: "ok")
        assert result == "ok"
        assert cb.get_state() == CircuitBreakerState.CLOSED

    def test_closed_failure_increments(self):
        """Failures increment the failure count."""
        cb = CircuitBreaker(failure_threshold=3)
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        assert cb.get_metrics()["failure_count"] == 1
        assert cb.get_state() == CircuitBreakerState.CLOSED

    def test_closed_to_open(self):
        """Circuit opens after reaching the failure threshold."""
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            with pytest.raises(ValueError):
                cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        assert cb.get_state() == CircuitBreakerState.OPEN

    def test_open_raises(self):
        """Open circuit immediately rejects calls."""
        cb = CircuitBreaker(failure_threshold=1, timeout_seconds=1000)
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        assert cb.get_state() == CircuitBreakerState.OPEN

        with pytest.raises(CircuitOpenError):
            cb.call(lambda: "ok")

    def test_open_to_half_open_after_timeout(self):
        """Circuit transitions to HALF_OPEN after timeout expires."""
        cb = CircuitBreaker(failure_threshold=1, timeout_seconds=0.01)
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        assert cb.get_state() == CircuitBreakerState.OPEN

        time.sleep(0.02)  # Wait for timeout to expire
        result = cb.call(lambda: "recovered")
        assert result == "recovered"
        # After one success in half-open, may still be half-open
        # (depends on success_threshold)

    def test_half_open_success_to_closed(self):
        """Circuit closes after enough successes in HALF_OPEN."""
        cb = CircuitBreaker(failure_threshold=1, success_threshold=2, timeout_seconds=0.01)
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        time.sleep(0.02)

        cb.call(lambda: "ok")
        assert cb.get_state() == CircuitBreakerState.HALF_OPEN
        cb.call(lambda: "ok")
        assert cb.get_state() == CircuitBreakerState.CLOSED

    def test_half_open_failure_to_open(self):
        """Any failure in HALF_OPEN immediately re-opens the circuit."""
        cb = CircuitBreaker(failure_threshold=1, success_threshold=3, timeout_seconds=0.01)
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        time.sleep(0.02)

        # First half-open call succeeds
        cb.call(lambda: "ok")
        assert cb.get_state() == CircuitBreakerState.HALF_OPEN

        # Second half-open call fails -> back to open
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail again")))
        assert cb.get_state() == CircuitBreakerState.OPEN

    def test_metrics(self):
        """Circuit breaker tracks metrics correctly."""
        cb = CircuitBreaker(failure_threshold=5)
        cb.call(lambda: "ok")
        cb.call(lambda: "ok")
        metrics = cb.get_metrics()
        assert metrics["total_calls"] == 2
        assert metrics["state"] == "closed"

    def test_multiple_transitions(self):
        """Circuit breaker tracks state transitions."""
        cb = CircuitBreaker(failure_threshold=1, success_threshold=1, timeout_seconds=0.01)
        # CLOSED -> OPEN
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        time.sleep(0.02)
        # OPEN -> HALF_OPEN -> CLOSED
        cb.call(lambda: "ok")
        assert cb.get_state() == CircuitBreakerState.CLOSED
        assert cb.get_metrics()["state_transitions_count"] >= 2


# ── Certificate ──


class TestCertificate:
    def test_is_valid(self):
        """Certificate is valid within its validity window."""
        now = time.time()
        cert = Certificate("web.svc", "root-ca", now - 3600, now + 3600)
        assert cert.is_valid(now) is True

    def test_is_expired(self):
        """Certificate is invalid after its validity window."""
        now = time.time()
        cert = Certificate("web.svc", "root-ca", now - 7200, now - 3600)
        assert cert.is_valid(now) is False

    def test_is_issued_by(self):
        """Certificate chain link is verified by issuer matching."""
        root = Certificate("root-ca", "root-ca", 0, 1e12, is_ca=True)
        leaf = Certificate("web.svc", "root-ca", 0, 1e12)
        assert leaf.is_issued_by(root) is True

    def test_not_issued_by(self):
        """Certificate not issued by a mismatched CA."""
        root = Certificate("other-ca", "other-ca", 0, 1e12, is_ca=True)
        leaf = Certificate("web.svc", "root-ca", 0, 1e12)
        assert leaf.is_issued_by(root) is False


# ── CertificateChain ──


class TestCertificateChain:
    def _make_valid_chain(self):
        now = time.time()
        root = Certificate("root-ca", "root-ca", now - 3600, now + 86400, is_ca=True)
        leaf = Certificate("web.svc", "root-ca", now - 3600, now + 86400)
        return CertificateChain([root, leaf])

    def test_valid_chain(self):
        """A properly constructed chain verifies successfully."""
        chain = self._make_valid_chain()
        valid, reason = chain.verify()
        assert valid is True
        assert reason == "valid"

    def test_expired_cert_fails(self):
        """Chain with an expired certificate fails verification."""
        now = time.time()
        root = Certificate("root-ca", "root-ca", now - 3600, now + 86400, is_ca=True)
        expired = Certificate("web.svc", "root-ca", now - 7200, now - 3600)
        chain = CertificateChain([root, expired])
        valid, reason = chain.verify()
        assert valid is False
        assert "expired" in reason

    def test_broken_chain_fails(self):
        """Chain where issuer doesn't match fails verification."""
        now = time.time()
        root = Certificate("root-ca", "root-ca", now - 3600, now + 86400, is_ca=True)
        leaf = Certificate("web.svc", "other-ca", now - 3600, now + 86400)
        chain = CertificateChain([root, leaf])
        valid, reason = chain.verify()
        assert valid is False
        assert "not issued by" in reason

    def test_root_not_ca_fails(self):
        """Chain where root is not a CA fails verification."""
        now = time.time()
        root = Certificate("root-ca", "root-ca", now - 3600, now + 86400, is_ca=False)
        leaf = Certificate("web.svc", "root-ca", now - 3600, now + 86400)
        chain = CertificateChain([root, leaf])
        valid, reason = chain.verify()
        assert valid is False
        assert "not a CA" in reason


# ── MtlsHandshake ──


class TestMtlsHandshake:
    def _make_chain(self, subject="svc"):
        now = time.time()
        root = Certificate("root-ca", "root-ca", now - 3600, now + 86400, is_ca=True)
        leaf = Certificate(subject, "root-ca", now - 3600, now + 86400)
        return CertificateChain([root, leaf])

    def _make_invalid_chain(self):
        now = time.time()
        root = Certificate("root-ca", "root-ca", now - 7200, now - 3600, is_ca=True)
        leaf = Certificate("svc", "root-ca", now - 7200, now - 3600)
        return CertificateChain([root, leaf])

    def test_both_valid_success(self):
        """mTLS succeeds when both chains are valid."""
        handshake = MtlsHandshake()
        ok, msg = handshake.handshake(self._make_chain("client"), self._make_chain("server"))
        assert ok is True
        assert "mutual authentication successful" in msg

    def test_client_invalid_fails(self):
        """mTLS fails when client chain is invalid."""
        handshake = MtlsHandshake()
        ok, msg = handshake.handshake(self._make_invalid_chain(), self._make_chain("server"))
        assert ok is False
        assert "client" in msg

    def test_server_invalid_fails(self):
        """mTLS fails when server chain is invalid."""
        handshake = MtlsHandshake()
        ok, msg = handshake.handshake(self._make_chain("client"), self._make_invalid_chain())
        assert ok is False
        assert "server" in msg


# ── CertificateRotation ──


class TestCertificateRotation:
    def test_should_rotate_true(self):
        """Certificate expiring within buffer should be rotated."""
        now = time.time()
        cert = Certificate("web.svc", "root-ca", now - 86400, now + 86400)  # expires in 1 day
        rotation = CertificateRotation()
        assert rotation.should_rotate(cert, buffer_days=30) is True

    def test_should_rotate_false(self):
        """Certificate with plenty of validity remaining should not rotate."""
        now = time.time()
        cert = Certificate("web.svc", "root-ca", now - 86400, now + 365 * 86400)
        rotation = CertificateRotation()
        assert rotation.should_rotate(cert, buffer_days=30) is False

    def test_rotate_creates_new(self):
        """Rotation creates a new certificate with same subject but new serial."""
        now = time.time()
        old = Certificate("web.svc", "root-ca", now - 86400, now + 86400,
                          serial_number="old-serial-1234")
        rotation = CertificateRotation()
        new = rotation.rotate(old)
        assert new.subject == old.subject
        assert new.issuer == old.issuer
        assert new.serial_number != old.serial_number
        assert new.is_valid()
