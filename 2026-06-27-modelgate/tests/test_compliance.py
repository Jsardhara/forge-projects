"""Tests for ModelGate compliance reporting."""

import json
import csv
import io
from datetime import datetime, timezone, timedelta

import pytest

from modelgate.compliance import (
    export_audit_csv,
    export_audit_json,
    export_grants_csv,
    format_report_text,
    generate_compliance_report,
)
from modelgate.models import (
    AccessGrant,
    AccessStatus,
    AuditEntry,
    ComplianceReport,
    ModelTier,
)
from modelgate.store import ModelGateStore


@pytest.fixture
def store(tmp_path):
    db_path = str(tmp_path / "test_compliance.db")
    s = ModelGateStore(db_path)
    yield s
    s.close()


class TestExportAuditCSV:
    def test_csv_format(self):
        entries = [
            AuditEntry(
                vid="a1",
                employee_email="alice@test.com",
                model_name="gpt-5.6",
                purpose="Work",
                accessed_at=datetime(2026, 6, 27, 12, 0, 0, tzinfo=timezone.utc),
                tier_at_access=ModelTier.CLASSIFIED,
            ),
        ]
        csv_text = export_audit_csv(entries)
        reader = csv.reader(io.StringIO(csv_text))
        rows = list(reader)
        assert len(rows) == 2  # header + data
        assert rows[0][0] == "audit_id"
        assert rows[1][1] == "alice@test.com"

    def test_csv_empty(self):
        csv_text = export_audit_csv([])
        reader = csv.reader(io.StringIO(csv_text))
        rows = list(reader)
        assert len(rows) == 1  # header only


class TestExportAuditJSON:
    def test_json_format(self):
        entries = [
            AuditEntry(
                vid="a1",
                employee_email="alice@test.com",
                model_name="gpt-5.6",
                purpose="Work",
                accessed_at=datetime(2026, 6, 27, 12, 0, 0, tzinfo=timezone.utc),
                tier_at_access=ModelTier.CLASSIFIED,
            ),
        ]
        json_text = export_audit_json(entries)
        data = json.loads(json_text)
        assert len(data) == 1
        assert data[0]["employee_email"] == "alice@test.com"
        assert data[0]["tier_at_access"] == "classified"

    def test_json_empty(self):
        json_text = export_audit_json([])
        data = json.loads(json_text)
        assert data == []


class TestExportGrantsCSV:
    def test_grants_csv(self):
        grants = [
            AccessGrant(
                vid="g1",
                employee_email="alice@test.com",
                tier=ModelTier.RESTRICTED,
                justification="Need restricted",
                approver="boss@test.com",
                granted_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
                expires_at=datetime(2026, 12, 31, tzinfo=timezone.utc),
                status=AccessStatus.ACTIVE,
            ),
        ]
        csv_text = export_grants_csv(grants)
        reader = csv.reader(io.StringIO(csv_text))
        rows = list(reader)
        assert len(rows) == 2
        assert rows[1][2] == "restricted"


class TestFormatReportText:
    def test_format_text(self):
        report = ComplianceReport(
            total_accesses=42,
            unique_employees=10,
            classified_accesses=5,
            government_vetted_accesses=2,
            expired_grants=1,
            revoked_grants=0,
            pending_requests=3,
        )
        text = format_report_text(report)
        assert "COMPLIANCE REPORT" in text
        assert "42" in text
        assert "10" in text
        assert "5" in text


class TestGenerateComplianceReport:
    def test_full_report(self, store):
        store.add_employee("alice@test.com", "Alice", "Engineering")
        store.log_access("alice@test.com", "gpt-5.6", "Work", ModelTier.CLASSIFIED)
        store.log_access("alice@test.com", "gpt-4o-mini", "Dev", ModelTier.PUBLIC)

        since = datetime.now(timezone.utc) - timedelta(hours=1)
        until = datetime.now(timezone.utc) + timedelta(hours=1)
        report = generate_compliance_report(store, since, until)
        assert report.total_accesses == 2
        assert report.classified_accesses == 1
