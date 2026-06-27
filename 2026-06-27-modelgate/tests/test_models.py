"""Tests for ModelGate data models."""

from datetime import datetime, timezone

from modelgate.models import (
    AccessGrant,
    AccessRequest,
    AccessRequestStatus,
    AccessStatus,
    AuditEntry,
    ComplianceReport,
    Employee,
    Model,
    ModelTier,
)


class TestModelTier:
    def test_tier_values(self):
        assert ModelTier.PUBLIC.value == "public"
        assert ModelTier.RESTRICTED.value == "restricted"
        assert ModelTier.CLASSIFIED.value == "classified"
        assert ModelTier.GOVERNMENT_VETTED.value == "government_vetted"

    def test_tier_from_value(self):
        assert ModelTier("public") == ModelTier.PUBLIC
        assert ModelTier("classified") == ModelTier.CLASSIFIED

    def test_all_tiers_exist(self):
        assert len(ModelTier) == 4


class TestAccessStatus:
    def test_status_values(self):
        assert AccessStatus.ACTIVE.value == "active"
        assert AccessStatus.EXPIRED.value == "expired"
        assert AccessStatus.REVOKED.value == "revoked"
        assert AccessStatus.PENDING.value == "pending"
        assert AccessStatus.DENIED.value == "denied"


class TestModel:
    def test_model_creation(self):
        m = Model(name="gpt-5.6", provider="OpenAI", tier=ModelTier.CLASSIFIED, description="Top model")
        assert m.name == "gpt-5.6"
        assert m.provider == "OpenAI"
        assert m.tier == ModelTier.CLASSIFIED
        assert m.description == "Top model"

    def test_model_frozen(self):
        m = Model(name="test", provider="Test", tier=ModelTier.PUBLIC)
        try:
            m.name = "changed"  # type: ignore
            assert False, "Should raise FrozenInstanceError"
        except AttributeError:
            pass

    def test_model_default_description(self):
        m = Model(name="test", provider="Test", tier=ModelTier.PUBLIC)
        assert m.description == ""


class TestEmployee:
    def test_employee_creation(self):
        emp = Employee(email="alice@test.com", name="Alice", department="Engineering")
        assert emp.email == "alice@test.com"
        assert emp.name == "Alice"
        assert emp.department == "Engineering"

    def test_employee_has_timestamp(self):
        emp = Employee(email="bob@test.com", name="Bob", department="Sales")
        assert emp.created_at is not None
        # Should be timezone-aware
        assert emp.created_at.tzinfo is not None


class TestAccessGrant:
    def test_grant_creation(self):
        grant = AccessGrant(
            vid="abc123",
            employee_email="alice@test.com",
            tier=ModelTier.RESTRICTED,
            justification="Need for project X",
            approver="boss@test.com",
        )
        assert grant.vid == "abc123"
        assert grant.tier == ModelTier.RESTRICTED
        assert grant.status == AccessStatus.ACTIVE
        assert grant.expires_at is None

    def test_grant_with_expiry(self):
        expires = datetime(2026, 12, 31, tzinfo=timezone.utc)
        grant = AccessGrant(
            vid="exp1",
            employee_email="alice@test.com",
            tier=ModelTier.CLASSIFIED,
            justification="Project classified work",
            approver="ciso@test.com",
            expires_at=expires,
        )
        assert grant.expires_at == expires


class TestAuditEntry:
    def test_audit_entry_creation(self):
        entry = AuditEntry(
            vid="a1",
            employee_email="alice@test.com",
            model_name="gpt-5.6",
            purpose="Customer support",
            tier_at_access=ModelTier.CLASSIFIED,
        )
        assert entry.vid == "a1"
        assert entry.model_name == "gpt-5.6"
        assert entry.tier_at_access == ModelTier.CLASSIFIED

    def test_audit_entry_immutable(self):
        entry = AuditEntry(
            vid="a1",
            employee_email="alice@test.com",
            model_name="gpt-4o",
            purpose="Testing",
            tier_at_access=ModelTier.PUBLIC,
        )
        try:
            entry.vid = "changed"  # type: ignore
            assert False, "Should be frozen"
        except AttributeError:
            pass


class TestComplianceReport:
    def test_default_report(self):
        report = ComplianceReport()
        assert report.total_accesses == 0
        assert report.unique_employees == 0
        assert report.classified_accesses == 0
        assert report.government_vetted_accesses == 0

    def test_report_with_data(self):
        report = ComplianceReport(
            total_accesses=150,
            unique_employees=45,
            classified_accesses=12,
            government_vetted_accesses=3,
            expired_grants=2,
            revoked_grants=1,
            pending_requests=5,
        )
        assert report.total_accesses == 150
        assert report.unique_employees == 45
