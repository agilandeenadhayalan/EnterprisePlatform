"""
M25: Kubernetes Fundamentals — Pod specs, deployments, services, and ingress.

This module models the core Kubernetes abstractions in pure Python so you
can understand how the control plane manages workloads without needing a
real cluster.
"""

from .pod_spec import PodStatus, ResourceRequirements, Container, PodSpec, PodLifecycle
from .deployment_controller import ReplicaSet, DeploymentController
from .service_discovery import ServiceType, Endpoint, KubernetesService, ServiceDiscovery
from .ingress_routing import IngressPath, IngressRule, IngressController
