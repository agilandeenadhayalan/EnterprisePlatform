"""
M41: Data Governance — lineage, PII detection, GDPR compliance, data catalog.

This module implements data governance foundations for mobility platforms:
tracking data lineage through processing pipelines, detecting and masking
personally identifiable information, managing GDPR consent and subject
rights, and maintaining a searchable data catalog with schema versioning.
"""

from .data_lineage import (
    DataNode,
    LineageEdge,
    LineageGraph,
    ImpactAnalyzer,
    LineageVisualizer,
)
from .pii_detection import (
    PIIType,
    PIIPattern,
    PIIFinding,
    PIIScanner,
    PIIMasker,
)
from .gdpr_compliance import (
    ConsentPurpose,
    ConsentRecord,
    ConsentManager,
    DataSubjectRight,
    SubjectRequest,
    DataSubjectRightsManager,
    RetentionPolicy,
)
from .data_catalog import (
    DataClassification,
    CatalogEntry,
    DataCatalog,
    SchemaVersion,
    SchemaRegistry,
)
