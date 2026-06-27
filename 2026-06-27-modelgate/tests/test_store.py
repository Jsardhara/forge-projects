"""Tests for ModelGate SQLite store."""

import os
import tempfile
from datetime import datetime, timezone, timedelta

import pytest

from modelgate.models import (
    AccessRequestStatus,
    AccessStatus,
    ModelTier,
)
from modelgate.store import ModelGateStore


@pytest.fixture
def store(tmp_path):
    """Create a temporary store for testing."""
    db_path = str(tmp_path / "test_modelgate.db")
    s = ModelGateStore(db_path)
    yield s
    s.close()


class TestEmployeeOps:
    def test_add_and_get_employee(self, store):
        emp = store.add_employee("alice@test.com", "Alice Chen", "Engineering")
        assert emp.email == "alice@test.com"
        assert emp.name == "Alice Chen"

        fetched = store.get_employee("alice@test.com")
        assert fetched is not None
        assert fetched.name == "Alice Chen"

    def test_get_nonexistent_employee(self, store):
        assert store.get_employee("nobody@test.com") is None

    def test_list_employees(self, store):
        store.add_employee("alice@test.com", "Alice", "Engineering")
        store.add_employee("bob@test.com", "Bob", "Sales")
        emps = store.list_employees()
        assert len(emps) == 2

    def test_update_employee(self, store):
        store.add_employee("alice@test.com", "Alice", "Engineering")
        updated = store.add_employee("alice@test.com", "Alice Chen", "DevOps")
        assert updated.name == "Alice Chen"
        assert updated.department == "DevOps"


class TestModelOps:
    def test_register_and_get_model(self, store):
        m = store.register_model("gpt-5.6", "OpenAI", ModelTier.CLASSIFIED, "Top model")
        assert m.name == "gpt-5.6"
        assert m.tier == ModelTier.CLASSIFIED

        fetched = store.get_model("gpt-5.6")
        assert fetched is not None
        assert fetched.provider == "OpenAI"

    def test_list_models(self, store):
        store.register_model("gpt-4o", "OpenAI", ModelTier.RESTRICTED)
        store.register_model("gpt-5.6", "OpenAI", ModelTier.CLASSIFIED)
        models = store.list_models()
        assert len(models) == 2

    def test_list_models_by_tier(self, store):
        store.register_model("gpt-4o", "OpenAI", ModelTier.RESTRICTED)
        store.register_model("gpt-5.6", "OpenAI", ModelTier.CLASSIFIED)
        store.register_model("gpt-4o-mini", "OpenAI", ModelTier.PUBLIC)
        restricted = store.list_models(tier=ModelTier.RESTRICTED)
        assert len(restricted) == 1
        assert restricted[0].name == "gpt-4o"

    def test_get_nonexistent_model(self, store):
        assert store.get_model("nonexistent") is None


class TestAccessGrants:
    def test_grant_access(self, store):
        store.add_employee("alice@test.com", "Alice", "Engineering")
        grant = store.grant_access(
            employee_email="alice@test.com",
            tier=ModelTier.RESTRICTED,
            justification="Working on AI integration project requirement",
            approver="boss@test.com",
        )
        assert grant.vid
        assert grant.tier == ModelTier.RESTRICTED
        assert grant.status == AccessStatus.ACTIVE

    def test_revoke_access(self, store):
        store.add_employee("alice@test.com", "Alice", "Engineering")
        grant = store.grant_access(
            employee_email="alice@test.com",
            tier=ModelTier.RESTRICTED,
            justification="Working on AI integration project requirement",
            approver="boss@test.com",
        )
        revoked = store.revoke_access(grant.vid)
        assert revoked is not None
        assert revoked.status == AccessStatus.REVOKED

    def test_list_grants_by_tier(self, store):
        store.add_employee("alice@test.com", "Alice", "Engineering")
        store.add_employee("bob@test.com", "Bob", "Sales")
        store.grant_access("alice@test.com", ModelTier.RESTRICTED, "Need restricted", "boss@test.com")
        store.grant_access("bob@test.com", ModelTier.CLASSIFIED, "Need classified access very important", "ciso@test.com")

        restricted = store.list_grants(tier=ModelTier.RESTRICTED)
        assert len(restricted) == 1

    def test_list_grants_by_status(self, store):
        store.add_employee("alice@test.com", "Alice", "Engineering")
        grant = store.grant_access("alice@test.com", ModelTier.RESTRICTED, "Need restricted", "boss@test.com")
        store.revoke_access(grant.vid)

        active = store.list_grants(status=AccessStatus.ACTIVE)
        assert len(active) == 0
        revoked = store.list_grants(status=AccessStatus.REVOKED)
        assert len(revoked) == 1


class TestAccessRequests:
    def test_create_request(self, store):
        store.add_employee("alice@test.com", "Alice", "Engineering")
        req = store.create_request(
            employee_email="alice@test.com",
            tier=ModelTier.CLASSIFIED,
            justification="Need classified access for government project work",
        )
        assert req.vid
        assert req.status == AccessRequestStatus.OPEN

    def test_approve_request(self, store):
        store.add_employee("alice@test.com", "Alice", "Engineering")
        req = store.create_request(
            employee_email="alice@test.com",
            tier=ModelTier.CLASSIFIED,
            justification="Need classified access for government project",
        )
        approved = store.approve_request(req.vid, "boss@test.com")
        assert approved is not None
        assert approved.status == AccessRequestStatus.APPROVED
        assert approved.reviewed_by == "boss@test.com"

    def test_deny_request(self, store):
        store.add_employee("alice@test.com", "Alice", "Engineering")
        req = store.create_request(
            employee_email="alice@test.com",
            tier=ModelTier.CLASSIFIED,
            justification="Need classified access for government work",
        )
        denied = store.deny_request(req.vid, "ciso@test.com", "Insufficient clearance")
        assert denied is not None
        assert denied.status == AccessRequestStatus.DENIED
        assert denied.denial_reason == "Insufficient clearance"


class TestAuditLog:
    def test_log_access(self, store):
        entry = store.log_access(
            employee_email="alice@test.com",
            model_name="gpt-5.6",
            purpose="Customer support automation",
            tier_at_access=ModelTier.CLASSIFIED,
        )
        assert entry.vid
        assert entry.model_name == "gpt-5.6"
        assert entry.tier_at_access == ModelTier.CLASSIFIED

    def test_list_audit_by_employee(self, store):
        store.log_access("alice@test.com", "gpt-4o", "Testing", ModelTier.RESTRICTED)
        store.log_access("bob@test.com", "gpt-4o-mini", "Dev", ModelTier.PUBLIC)
        store.log_access("alice@test.com", "gpt-5.6", "Gov work", ModelTier.CLASSIFIED)

        alice_logs = store.list_audit(employee_email="alice@test.com")
        assert len(alice_logs) == 2

    def test_list_audit_by_tier(self, store):
        store.log_access("alice@test.com", "gpt-4o", "Testing", ModelTier.RESTRICTED)
        store.log_access("bob@test.com", "gpt-5.6", "Gov work", ModelTier.CLASSIFIED)

        classified = store.list_audit(tier=ModelTier.CLASSIFIED)
        assert len(classified) == 1

    def test_list_audit_by_date_range(self, store):
        store.log_access("alice@test.com", "gpt-4o", "Testing", ModelTier.RESTRICTED)
        store.log_access("bob@test.com", "gpt-4o-mini", "Dev", ModelTier.PUBLIC)

        since = datetime.now(timezone.utc) - timedelta(hours=1)
        until = datetime.now(timezone.utc) + timedelta(hours=1)
        recent = store.list_audit(since=since, until=until)
        assert len(recent) == 2


class TestAccessCheck:
    def test_check_access_with_grant(self, store):
        store.add_employee("alice@test.com", "Alice", "Engineering")
        store.grant_access("alice@test.com", ModelTier.RESTRICTED, "Need restricted", "boss@test.com")
        assert store.check_access("alice@test.com", ModelTier.RESTRICTED) is True

    def test_check_access_without_grant(self, store):
        store.add_employee("alice@test.com", "Alice", "Engineering")
        assert store.check_access("alice@test.com", ModelTier.CLASSIFIED) is False


class TestComplianceReport:
    def test_generate_report(self, store):
        store.add_employee("alice@test.com", "Alice", "Engineering")
        store.add_employee("bob@test.com", "Bob", "Sales")
        store.grant_access("alice@test.com", ModelTier.RESTRICTED, "Need restricted", "boss@test.com")
        store.log_access("alice@test.com", "gpt-4o", "Work", ModelTier.RESTRICTED)
        store.log_access("bob@test.com", "gpt-5.6", "Gov project", ModelTier.CLASSIFIED)
        store.log_access("alice@test.com", "gpt-5.6-classified", "Super secret", ModelTier.GOVERNMENT_VETTED)

        since = datetime.now(timezone.utc) - timedelta(hours=1)
        until = datetime.now(timezone.utc) + timedelta(hours=1)
        report = store.generate_report(since, until)
        assert report.total_accesses == 3
        assert report.unique_employees == 2
        assert report.classified_accesses == 2  # classified + gov_vetted
        assert report.government_vetted_accesses == 1


class TestAccessReview:
    def test_expire_stale_grants(self, store):
        store.add_employee("alice@test.com", "Alice", "Engineering")
        # Grant with past expiry — should be expired
        past = datetime.now(timezone.utc) - timedelta(days=1)
        store.grant_access(
            "alice@test.com", ModelTier.RESTRICTED, "Need restricted",
            "boss@test.com", expires_at=past,
        )
        count = store.expire_stale_grants()
        assert count == 1

        active = store.list_grants(status=AccessStatus.ACTIVE)
        assert len(active) == 0

    def test_review_expired_grants(self, store):
        store.add_employee("alice@test.com", "Alice", "Engineering")
        past = datetime.now(timezone.utc) - timedelta(days=1)
        store.grant_access(
            "alice@test.com", ModelTier.RESTRICTED, "Need restricted",
            "boss@test.com", expires_at=past,
        )
        expired = store.review_expired_grants()
        assert len(expired) == 1
