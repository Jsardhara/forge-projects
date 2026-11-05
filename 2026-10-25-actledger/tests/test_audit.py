import unittest

from actledger.audit import audit, is_consequential
from actledger.chain import GENESIS_HASH, make_entry
from actledger.manifest import DIGEST_TAG
from actledger.models import ActionRecord, SEVERITY_RANK, Severity

MEASURED = DIGEST_TAG + "a" * 64


def entry(seq, **kw):
    kw.setdefault("tool", "file.read")
    kw.setdefault("outcome", "ok")
    kw.setdefault("verifier", "sentinel")
    kw.setdefault("model_id", "deepseek/deepseek-v4.1")
    kw.setdefault("model_digest", MEASURED)
    kw.setdefault("policy_version", "pol-1")
    record = ActionRecord(agent_id=kw.pop("agent_id", "forge"), **kw)
    return make_entry(seq, GENESIS_HASH if seq == 0 else "f" * 64, record)


def codes(report):
    return sorted({finding.code for finding in report.findings})


class TestIsConsequential(unittest.TestCase):
    def test_write_shell_publish_are_consequential(self):
        for tool in ("file.write", "shell.exec", "publish.post", "trade.place", "credential.rotate"):
            self.assertTrue(is_consequential(tool), tool)

    def test_read_and_search_are_not(self):
        for tool in ("file.read", "search.grep", "ledger.verify"):
            self.assertFalse(is_consequential(tool), tool)

    def test_is_case_insensitive(self):
        self.assertTrue(is_consequential("FILE.WRITE"))


class TestAuditFindings(unittest.TestCase):
    def test_unverified_action_is_flagged(self):
        report = audit([entry(0, verifier="")])
        self.assertIn("AAL-001", codes(report))
        self.assertEqual(report.unverified, 1)

    def test_fully_verified_ledger_has_no_unverified(self):
        report = audit([entry(0), entry(1)])
        self.assertEqual(report.unverified, 0)
        self.assertNotIn("AAL-001", codes(report))
        self.assertIn("AAL-006", codes(report))

    def test_consequential_action_without_approval_is_flagged(self):
        report = audit([entry(0, tool="file.write")])
        self.assertIn("AAL-002", codes(report))

    def test_consequential_action_with_approval_is_not_flagged(self):
        report = audit([entry(0, tool="file.write", approved_by="jyot", approved_at="2026-10-25T06:00Z")])
        self.assertNotIn("AAL-002", codes(report))

    def test_approval_needs_both_who_and_when(self):
        report = audit([entry(0, tool="file.write", approved_by="jyot")])
        self.assertIn("AAL-002", codes(report))

    def test_read_action_needs_no_approval(self):
        report = audit([entry(0, tool="file.read")])
        self.assertNotIn("AAL-002", codes(report))

    def test_self_verification_is_warned(self):
        report = audit([entry(0, verifier="forge")])
        self.assertIn("AAL-003", codes(report))

    def test_missing_model_digest_is_warned(self):
        report = audit([entry(0, model_digest="")])
        self.assertIn("AAL-004", codes(report))

    def test_missing_policy_version_is_warned(self):
        report = audit([entry(0, policy_version="")])
        self.assertIn("AAL-005", codes(report))

    def test_verdict_is_severity_dominant(self):
        report = audit([entry(0, verifier="")])
        self.assertEqual(report.severity, Severity.FLAG)
        warns_only = audit([entry(0, model_digest="")])
        self.assertEqual(warns_only.severity, Severity.WARN)

    def test_clean_ledger_is_pass(self):
        entries = [entry(0), entry(1)]
        bindings = {item.seq: MEASURED for item in entries}
        report = audit(entries, bindings)
        self.assertEqual(report.severity, Severity.PASS)

    def test_a_typed_digest_is_not_a_measured_one(self):
        # The pre-2026-11-05 behaviour was PASS here: any non-empty string counted.
        # A free-form digest is a transcription, so it is reported, not accepted.
        report = audit([entry(0, model_digest="sha256:abc123")])
        self.assertIn("AAL-007", codes(report))
        self.assertEqual(report.severity, Severity.WARN)

    def test_a_tag_without_a_binding_is_still_unmeasured(self):
        report = audit([entry(0)])  # tagged digest, no bindings passed
        self.assertIn("AAL-007", codes(report))

    def test_empty_ledger_is_pass_and_reports_zero(self):
        report = audit([])
        self.assertEqual(report.total, 0)
        self.assertEqual(report.severity, Severity.PASS)

    def test_counts_are_consistent_with_findings(self):
        report = audit([entry(0, verifier=""), entry(1, verifier=""), entry(2)])
        self.assertEqual(report.total, 3)
        self.assertEqual(report.unverified, 2)
        self.assertEqual(report.independent_verified, 1)

    def test_fail_on_threshold_decides_exit_ok(self):
        warns_only = audit([entry(0, model_digest="")])
        self.assertTrue(warns_only.acceptable("FLAG"))
        self.assertFalse(warns_only.acceptable("WARN"))
        self.assertTrue(warns_only.acceptable("NONE"))

    def test_every_finding_has_detail(self):
        report = audit([entry(0, verifier="", model_digest="", policy_version="", tool="file.write")])
        for finding in report.findings:
            self.assertTrue(finding.detail)
            self.assertIn(finding.severity, SEVERITY_RANK)


if __name__ == "__main__":
    unittest.main()
