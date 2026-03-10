"""
Tests for M41: Data Governance — lineage, PII detection, GDPR compliance, data catalog.
"""

import re
from datetime import datetime, timedelta

import pytest

from m41_data_governance.data_lineage import (
    DataNode,
    LineageEdge,
    LineageGraph,
    ImpactAnalyzer,
    LineageVisualizer,
)
from m41_data_governance.pii_detection import (
    PIIType,
    PIIPattern,
    PIIFinding,
    PIIScanner,
    PIIMasker,
)
from m41_data_governance.gdpr_compliance import (
    ConsentPurpose,
    ConsentRecord,
    ConsentManager,
    DataSubjectRight,
    SubjectRequest,
    DataSubjectRightsManager,
    RetentionPolicy,
)
from m41_data_governance.data_catalog import (
    DataClassification,
    CatalogEntry,
    DataCatalog,
    SchemaVersion,
    SchemaRegistry,
)


# ── LineageGraph ──


class TestLineageGraph:
    def _build_graph(self):
        """Build: source -> etl -> warehouse -> dashboard."""
        g = LineageGraph()
        g.add_node(DataNode("src", "Raw GPS", "source"))
        g.add_node(DataNode("etl", "Clean ETL", "transform"))
        g.add_node(DataNode("wh", "Data Warehouse", "transform"))
        g.add_node(DataNode("dash", "Dashboard", "sink"))
        g.add_edge(LineageEdge("src", "etl", "map", "Clean raw data"))
        g.add_edge(LineageEdge("etl", "wh", "aggregate", "Aggregate trips"))
        g.add_edge(LineageEdge("wh", "dash", "map", "Render charts"))
        return g

    def test_add_and_get_node(self):
        """Nodes are retrievable by ID."""
        g = LineageGraph()
        g.add_node(DataNode("n1", "Test", "source"))
        assert g.get_node("n1").name == "Test"

    def test_get_unknown_node(self):
        """Unknown node ID returns None."""
        g = LineageGraph()
        assert g.get_node("nonexistent") is None

    def test_edges_from(self):
        """Forward edges from a node."""
        g = self._build_graph()
        edges = g.get_edges_from("etl")
        assert len(edges) == 1
        assert edges[0].target_id == "wh"

    def test_edges_to(self):
        """Backward edges to a node."""
        g = self._build_graph()
        edges = g.get_edges_to("wh")
        assert len(edges) == 1
        assert edges[0].source_id == "etl"

    def test_trace_upstream(self):
        """Trace upstream finds all ancestors."""
        g = self._build_graph()
        upstream = g.trace_upstream("dash")
        assert set(upstream) == {"src", "etl", "wh"}

    def test_trace_downstream(self):
        """Trace downstream finds all descendants."""
        g = self._build_graph()
        downstream = g.trace_downstream("src")
        assert set(downstream) == {"etl", "wh", "dash"}

    def test_full_lineage(self):
        """Full lineage returns both upstream and downstream."""
        g = self._build_graph()
        lineage = g.get_full_lineage("etl")
        assert "src" in lineage["upstream"]
        assert "wh" in lineage["downstream"]
        assert "dash" in lineage["downstream"]


# ── ImpactAnalyzer ──


class TestImpactAnalyzer:
    def _build_graph(self):
        g = LineageGraph()
        g.add_node(DataNode("src", "Source", "source", metadata={"criticality": "high"}))
        g.add_node(DataNode("t1", "Transform", "transform"))
        g.add_node(DataNode("sink1", "Sink", "sink"))
        g.add_edge(LineageEdge("src", "t1", "map"))
        g.add_edge(LineageEdge("t1", "sink1", "map"))
        return g

    def test_analyze_change(self):
        """Change impact returns downstream nodes."""
        g = self._build_graph()
        analyzer = ImpactAnalyzer()
        affected = analyzer.analyze_change(g, "src")
        assert "t1" in affected
        assert "sink1" in affected

    def test_analyze_change_leaf(self):
        """Leaf node change affects nothing downstream."""
        g = self._build_graph()
        analyzer = ImpactAnalyzer()
        affected = analyzer.analyze_change(g, "sink1")
        assert affected == []

    def test_critical_paths(self):
        """Critical paths connect sources to sinks through critical nodes."""
        g = self._build_graph()
        analyzer = ImpactAnalyzer()
        paths = analyzer.get_critical_paths(g)
        assert len(paths) >= 1
        assert ("src", "sink1") in paths

    def test_no_critical_nodes(self):
        """No critical nodes means no critical paths."""
        g = LineageGraph()
        g.add_node(DataNode("a", "A", "source"))
        g.add_node(DataNode("b", "B", "sink"))
        g.add_edge(LineageEdge("a", "b", "map"))
        analyzer = ImpactAnalyzer()
        paths = analyzer.get_critical_paths(g)
        assert paths == []


# ── LineageVisualizer ──


class TestLineageVisualizer:
    def test_ascii_output(self):
        """ASCII visualization shows node and children."""
        g = LineageGraph()
        g.add_node(DataNode("a", "Source A", "source"))
        g.add_node(DataNode("b", "ETL B", "transform"))
        g.add_edge(LineageEdge("a", "b", "map"))
        viz = LineageVisualizer()
        text = viz.to_ascii(g, "a")
        assert "[Source A]" in text
        assert "[ETL B]" in text
        assert "(map)" in text

    def test_ascii_no_children(self):
        """Node with no children shows just its name."""
        g = LineageGraph()
        g.add_node(DataNode("leaf", "Leaf Node", "sink"))
        viz = LineageVisualizer()
        text = viz.to_ascii(g, "leaf")
        assert "[Leaf Node]" in text
        assert "->" not in text

    def test_ascii_unknown_node(self):
        """Unknown node shows its ID."""
        g = LineageGraph()
        viz = LineageVisualizer()
        text = viz.to_ascii(g, "missing")
        assert "missing" in text


# ── PIIScanner ──


class TestPIIScanner:
    def test_ssn_detection(self):
        """Scanner detects SSN patterns."""
        scanner = PIIScanner()
        findings = scanner.scan("My SSN is 123-45-6789")
        assert len(findings) >= 1
        assert any(f.pii_type == PIIType.SSN for f in findings)

    def test_email_detection(self):
        """Scanner detects email addresses."""
        scanner = PIIScanner()
        findings = scanner.scan("Contact: user@example.com")
        assert any(f.pii_type == PIIType.EMAIL for f in findings)

    def test_phone_detection(self):
        """Scanner detects phone numbers."""
        scanner = PIIScanner()
        findings = scanner.scan("Call 555-123-4567")
        assert any(f.pii_type == PIIType.PHONE for f in findings)

    def test_credit_card_detection(self):
        """Scanner detects credit card numbers."""
        scanner = PIIScanner()
        findings = scanner.scan("Card: 4111-1111-1111-1111")
        assert any(f.pii_type == PIIType.CREDIT_CARD for f in findings)

    def test_ip_detection(self):
        """Scanner detects IP addresses."""
        scanner = PIIScanner()
        findings = scanner.scan("Server at 192.168.1.100")
        assert any(f.pii_type == PIIType.IP_ADDRESS for f in findings)

    def test_no_pii(self):
        """Clean text returns no findings."""
        scanner = PIIScanner()
        findings = scanner.scan("This is a normal sentence.")
        assert len(findings) == 0

    def test_custom_pattern(self):
        """Custom patterns are scanned."""
        scanner = PIIScanner()
        scanner.add_pattern(PIIPattern(
            pii_type=PIIType.PASSPORT,
            pattern=r"\b[A-Z]\d{8}\b",
            description="Passport number",
            risk_level="high",
        ))
        findings = scanner.scan("Passport: A12345678")
        assert any(f.pii_type == PIIType.PASSPORT for f in findings)


# ── PIIMasker ──


class TestPIIMasker:
    def test_redact(self):
        """Redact strategy replaces with [REDACTED]."""
        masker = PIIMasker()
        assert masker.mask("123-45-6789", "redact") == "[REDACTED]"

    def test_partial(self):
        """Partial strategy shows last 4 chars."""
        masker = PIIMasker()
        result = masker.mask("123-45-6789", "partial")
        assert result.endswith("6789")
        assert result.startswith("***")

    def test_hash(self):
        """Hash strategy returns first 8 chars of SHA256."""
        masker = PIIMasker()
        result = masker.mask("test@email.com", "hash")
        assert len(result) == 8

    def test_mask_text(self):
        """Mask text replaces all findings in place."""
        scanner = PIIScanner()
        masker = PIIMasker()
        text = "SSN: 123-45-6789"
        findings = scanner.scan(text)
        masked = masker.mask_text(text, findings)
        assert "123-45-6789" not in masked
        assert "[REDACTED]" in masked

    def test_mask_text_multiple(self):
        """Multiple PII items are all masked."""
        scanner = PIIScanner()
        masker = PIIMasker()
        text = "SSN: 123-45-6789 email: user@test.com"
        findings = scanner.scan(text)
        masked = masker.mask_text(text, findings)
        assert "123-45-6789" not in masked
        assert "user@test.com" not in masked


# ── ConsentManager ──


class TestConsentManager:
    def test_grant_consent(self):
        """Granting consent creates a record."""
        mgr = ConsentManager()
        record = mgr.grant("user@test.com", ConsentPurpose.MARKETING)
        assert record.granted is True
        assert record.purpose == ConsentPurpose.MARKETING

    def test_check_active_consent(self):
        """Active consent returns True."""
        mgr = ConsentManager()
        mgr.grant("user@test.com", ConsentPurpose.ANALYTICS)
        assert mgr.check("user@test.com", ConsentPurpose.ANALYTICS) is True

    def test_check_no_consent(self):
        """No consent record returns False."""
        mgr = ConsentManager()
        assert mgr.check("user@test.com", ConsentPurpose.MARKETING) is False

    def test_withdraw_consent(self):
        """Withdrawing consent makes check return False."""
        mgr = ConsentManager()
        mgr.grant("user@test.com", ConsentPurpose.MARKETING)
        mgr.withdraw("user@test.com", ConsentPurpose.MARKETING)
        assert mgr.check("user@test.com", ConsentPurpose.MARKETING) is False

    def test_get_all_records(self):
        """Get all returns full history for a subject."""
        mgr = ConsentManager()
        mgr.grant("user@test.com", ConsentPurpose.MARKETING)
        mgr.grant("user@test.com", ConsentPurpose.ANALYTICS)
        records = mgr.get_all("user@test.com")
        assert len(records) == 2

    def test_different_subjects_independent(self):
        """Consent is per-subject."""
        mgr = ConsentManager()
        mgr.grant("a@test.com", ConsentPurpose.MARKETING)
        assert mgr.check("a@test.com", ConsentPurpose.MARKETING) is True
        assert mgr.check("b@test.com", ConsentPurpose.MARKETING) is False


# ── DataSubjectRightsManager ──


class TestDataSubjectRightsManager:
    def test_submit_request(self):
        """Submitting a request creates pending status with 30-day due date."""
        mgr = DataSubjectRightsManager()
        req = mgr.submit_request("user@test.com", DataSubjectRight.ACCESS)
        assert req.status == "pending"
        assert req.right == DataSubjectRight.ACCESS
        delta = req.due_date - req.submitted_at
        assert 29 <= delta.days <= 30

    def test_process_request(self):
        """Processing transitions to 'processing' status."""
        mgr = DataSubjectRightsManager()
        req = mgr.submit_request("user@test.com", DataSubjectRight.ERASURE)
        processed = mgr.process_request(req.id)
        assert processed.status == "processing"

    def test_complete_request(self):
        """Completing sets status and timestamp."""
        mgr = DataSubjectRightsManager()
        req = mgr.submit_request("user@test.com", DataSubjectRight.PORTABILITY)
        mgr.complete_request(req.id)
        assert req.status == "completed"
        assert req.completed_at is not None

    def test_is_overdue_not_completed(self):
        """Non-completed request past due date is overdue."""
        mgr = DataSubjectRightsManager()
        req = mgr.submit_request("user@test.com", DataSubjectRight.ACCESS)
        # Force the due date to be in the past
        req.due_date = datetime.utcnow() - timedelta(days=1)
        assert mgr.is_overdue(req.id) is True

    def test_is_not_overdue(self):
        """Fresh request is not overdue."""
        mgr = DataSubjectRightsManager()
        req = mgr.submit_request("user@test.com", DataSubjectRight.ACCESS)
        assert mgr.is_overdue(req.id) is False

    def test_completed_not_overdue(self):
        """Completed request is never overdue."""
        mgr = DataSubjectRightsManager()
        req = mgr.submit_request("user@test.com", DataSubjectRight.ACCESS)
        req.due_date = datetime.utcnow() - timedelta(days=1)
        mgr.complete_request(req.id)
        assert mgr.is_overdue(req.id) is False


# ── RetentionPolicy ──


class TestRetentionPolicy:
    def test_default_retention(self):
        """Data older than default retention is purgeable."""
        policy = RetentionPolicy(default_retention_days=90)
        old_date = datetime.utcnow() - timedelta(days=100)
        assert policy.should_purge("unknown_category", old_date) is True

    def test_within_retention(self):
        """Data within retention period is not purgeable."""
        policy = RetentionPolicy(default_retention_days=90)
        recent = datetime.utcnow() - timedelta(days=30)
        assert policy.should_purge("any", recent) is False

    def test_custom_rule(self):
        """Category-specific rules override default."""
        policy = RetentionPolicy(default_retention_days=365)
        policy.add_rule("logs", 30)
        old_logs = datetime.utcnow() - timedelta(days=45)
        assert policy.should_purge("logs", old_logs) is True
        # Same date for different category uses default
        assert policy.should_purge("other", old_logs) is False

    def test_get_purgeable(self):
        """Get purgeable returns items past retention."""
        policy = RetentionPolicy(default_retention_days=30)
        items = [
            ("logs", datetime.utcnow() - timedelta(days=60)),
            ("data", datetime.utcnow() - timedelta(days=10)),
            ("old", datetime.utcnow() - timedelta(days=45)),
        ]
        purgeable = policy.get_purgeable(items)
        assert len(purgeable) == 2

    def test_empty_list(self):
        """Empty list returns empty purgeable."""
        policy = RetentionPolicy()
        assert policy.get_purgeable([]) == []


# ── DataCatalog ──


class TestDataCatalog:
    def test_register_and_get(self):
        """Register and retrieve a catalog entry."""
        catalog = DataCatalog()
        entry = CatalogEntry("d1", "Trip Data", "All trip records", "platform", DataClassification.CONFIDENTIAL)
        catalog.register(entry)
        assert catalog.get("d1").name == "Trip Data"

    def test_get_unknown(self):
        """Unknown ID returns None."""
        catalog = DataCatalog()
        assert catalog.get("nope") is None

    def test_search_by_name(self):
        """Search matches by name."""
        catalog = DataCatalog()
        catalog.register(CatalogEntry("d1", "Trip Data", "desc", "owner", DataClassification.INTERNAL))
        catalog.register(CatalogEntry("d2", "Driver Scores", "desc", "owner", DataClassification.INTERNAL))
        results = catalog.search("trip")
        assert len(results) == 1
        assert results[0].id == "d1"

    def test_search_by_tag(self):
        """Search matches by tag."""
        catalog = DataCatalog()
        catalog.register(CatalogEntry("d1", "Data", "desc", "owner", DataClassification.INTERNAL, tags=["mobility"]))
        results = catalog.search("mobility")
        assert len(results) == 1

    def test_classify(self):
        """Classification level can be updated."""
        catalog = DataCatalog()
        catalog.register(CatalogEntry("d1", "Data", "desc", "owner", DataClassification.INTERNAL))
        catalog.classify("d1", DataClassification.RESTRICTED)
        assert catalog.get("d1").classification == DataClassification.RESTRICTED

    def test_by_owner(self):
        """Filter by owner."""
        catalog = DataCatalog()
        catalog.register(CatalogEntry("d1", "A", "desc", "alice", DataClassification.INTERNAL))
        catalog.register(CatalogEntry("d2", "B", "desc", "bob", DataClassification.INTERNAL))
        assert len(catalog.by_owner("alice")) == 1


# ── SchemaRegistry ──


class TestSchemaRegistry:
    def test_register_first(self):
        """First schema is version 1."""
        registry = SchemaRegistry()
        sv = registry.register_schema("trips", {"id": "int", "name": "str"})
        assert sv.version == 1

    def test_register_increments(self):
        """Each registration increments version."""
        registry = SchemaRegistry()
        registry.register_schema("trips", {"id": "int"})
        sv2 = registry.register_schema("trips", {"id": "int", "status": "str"})
        assert sv2.version == 2

    def test_get_latest(self):
        """Latest returns the most recent version."""
        registry = SchemaRegistry()
        registry.register_schema("trips", {"id": "int"})
        registry.register_schema("trips", {"id": "int", "status": "str"})
        latest = registry.get_latest("trips")
        assert latest.version == 2
        assert "status" in latest.schema

    def test_get_latest_unknown(self):
        """Unknown dataset returns None."""
        registry = SchemaRegistry()
        assert registry.get_latest("nope") is None

    def test_backward_compatible(self):
        """Adding fields is backward compatible."""
        registry = SchemaRegistry()
        registry.register_schema("trips", {"id": "int", "name": "str"})
        new_schema = {"id": "int", "name": "str", "status": "str"}
        assert registry.check_compatibility("trips", new_schema, "backward") is True

    def test_backward_incompatible(self):
        """Removing fields is not backward compatible."""
        registry = SchemaRegistry()
        registry.register_schema("trips", {"id": "int", "name": "str"})
        new_schema = {"id": "int"}
        assert registry.check_compatibility("trips", new_schema, "backward") is False

    def test_forward_compatible(self):
        """Removing fields is forward compatible."""
        registry = SchemaRegistry()
        registry.register_schema("trips", {"id": "int", "name": "str", "extra": "str"})
        new_schema = {"id": "int", "name": "str"}
        assert registry.check_compatibility("trips", new_schema, "forward") is True
