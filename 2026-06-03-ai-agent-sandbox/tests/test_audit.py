"""Tests for the Audit Logger."""
import json
import os
import tempfile
import pytest
from ai_agent_sandbox.audit import AuditLogger


class TestAuditLogger:
    def test_log_entry(self):
        logger = AuditLogger()
        entry = logger.log("network", "https://example.com", True)
        assert entry.category == "network"
        assert entry.allowed is True
        assert logger.entry_count == 1

    def test_get_violations(self):
        logger = AuditLogger()
        logger.log("network", "https://evil.com", False, severity="warning")
        logger.log("network", "https://good.com", True)
        violations = logger.get_violations()
        assert len(violations) == 1
        assert violations[0].action == "https://evil.com"

    def test_get_critical(self):
        logger = AuditLogger()
        logger.log("system", "kill_switch", True, severity="critical")
        logger.log("network", "normal", True, severity="info")
        critical = logger.get_critical()
        assert len(critical) == 1

    def test_export_json(self):
        logger = AuditLogger()
        logger.log("network", "https://example.com", True)
        logger.log("filesystem", "/etc/passwd", False)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            count = logger.export_json(path)
            assert count == 2
            with open(path) as f:
                data = json.load(f)
            assert len(data) == 2
            assert data[0]["category"] == "network"
        finally:
            os.unlink(path)

    def test_summary(self):
        logger = AuditLogger()
        logger.log("network", "url1", True)
        logger.log("network", "url2", False)
        logger.log("filesystem", "file1", True)
        summary = logger.summary()
        assert summary["total_entries"] == 3
        assert summary["violations"] == 1
        assert summary["by_category"]["network"] == 2
        assert summary["by_category"]["filesystem"] == 1

    def test_filter_by_category(self):
        logger = AuditLogger()
        logger.log("network", "url1", True)
        logger.log("filesystem", "file1", True)
        entries = logger.get_entries(category="network")
        assert len(entries) == 1

    def test_filter_by_severity(self):
        logger = AuditLogger()
        logger.log("system", "kill", True, severity="critical")
        logger.log("network", "url", True, severity="info")
        entries = logger.get_entries(severity="critical")
        assert len(entries) == 1
