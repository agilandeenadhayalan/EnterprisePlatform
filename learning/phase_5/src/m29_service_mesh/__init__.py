"""
M29: Service Mesh Basics — Sidecar proxies, traffic routing, circuit breakers,
and mutual TLS.

This module models the core service mesh abstractions in pure Python so you
can understand how Istio, Linkerd, and Envoy work without needing a real
mesh deployment.
"""

from .sidecar_proxy import ProxyConfig, Request, Response, SidecarProxy
from .traffic_routing import TrafficRule, WeightedRouter, HeaderBasedRouter
from .circuit_breaker import CircuitBreakerState, CircuitBreaker, CircuitOpenError
from .mtls import Certificate, CertificateChain, MtlsHandshake, CertificateRotation
