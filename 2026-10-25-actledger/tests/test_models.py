import unittest

from actledger.models import (
    ActionRecord,
    AuditFinding,
    SEVERITY_RANK,
    Severity,
    worst_severity,
)


class TestActionRecord(unittest.TestCase):
    def test_record_is_frozen(self):
        record = ActionRecord(agent_id="forge", tool="file.write", outcome="ok")
        with self.assertRaises(Exception):
            record.agent_id = "someone-else"  # type: ignore[misc]

    def test_to_dict_keeps_every_field(self):
        record = ActionRecord(
            agent_id="forge",
            tool="file.write",
            outcome="ok",
            verifier="sentinel",
            data_touched=("a.txt", "b.txt"),
        )
        payload = record.to_dict()
        self.assertEqual(payload["agent_id"], "forge")
        self.assertEqual(payload["verifier"], "sentinel")
        self.assertEqual(payload["data_touched"], ["a.txt", "b.txt"])

    def test_to_dict_is_json_ready(self):
        import json

        payload = ActionRecord(agent_id="a", tool="t", outcome="o").to_dict()
        json.dumps(payload)  # must not raise

    def test_data_touched_defaults_empty_and_is_a_tuple(self):
        record = ActionRecord(agent_id="a", tool="t", outcome="o")
        self.assertEqual(record.data_touched, ())
        self.assertIsInstance(record.data_touched, tuple)

    def test_missing_required_field_raises(self):
        with self.assertRaises(TypeError):
            ActionRecord(agent_id="a", tool="t")  # type: ignore[call-arg]


class TestSeverity(unittest.TestCase):
    def test_rank_orders_info_warn_flag(self):
        self.assertLess(SEVERITY_RANK[Severity.INFO], SEVERITY_RANK[Severity.WARN])
        self.assertLess(SEVERITY_RANK[Severity.WARN], SEVERITY_RANK[Severity.FLAG])

    def test_worst_severity_is_dominant_not_summed(self):
        findings = (
            AuditFinding(code="A", severity=Severity.WARN, detail="x"),
            AuditFinding(code="B", severity=Severity.WARN, detail="y"),
            AuditFinding(code="C", severity=Severity.INFO, detail="z"),
        )
        self.assertEqual(worst_severity(findings), Severity.WARN)

    def test_worst_severity_of_empty_is_pass(self):
        self.assertEqual(worst_severity(()), Severity.PASS)

    def test_worst_severity_picks_flag_over_many_warns(self):
        findings = tuple(
            AuditFinding(code="W", severity=Severity.WARN, detail="w") for _ in range(9)
        ) + (AuditFinding(code="F", severity=Severity.FLAG, detail="f"),)
        self.assertEqual(worst_severity(findings), Severity.FLAG)


if __name__ == "__main__":
    unittest.main()
