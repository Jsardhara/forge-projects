import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest

from actledger.cli import main


def run(argv):
    out = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


class CliTestCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="actledger-cli-")
        self.ledger = os.path.join(self.dir, "actions.jsonl")
        self.addCleanup(shutil.rmtree, self.dir, True)

    def record(self, **flags):
        argv = ["record", "--ledger", self.ledger, "--agent", "forge", "--tool", "file.read", "--outcome", "ok"]
        for key, value in flags.items():
            argv.append("--%s=%s" % (key.replace("_", "-"), value))
        return run(argv)


class TestRecord(CliTestCase):
    def test_record_writes_a_line_and_returns_zero(self):
        code, out, _ = self.record()
        self.assertEqual(code, 0)
        self.assertIn("seq 0", out)
        self.assertTrue(os.path.exists(self.ledger))

    def test_record_accepts_all_evidence_fields(self):
        code, _, _ = self.record(
            model="deepseek/deepseek-v4.1",
            model_digest="sha256:deadbeef",
            policy="pol-7",
            args_text="--force",
            data="a.txt",
            verifier="sentinel",
            approved_by="jyot",
            approved_at="2026-10-25T06:00:00Z",
            ts="2026-10-25T06:41:00Z",
        )
        self.assertEqual(code, 0)
        code, out, _ = run(["tail", "--ledger", self.ledger, "-n", "1"])
        self.assertEqual(code, 0)
        self.assertIn("sentinel", out)

    def test_missing_required_flag_is_usage_error(self):
        code, _, err = run(["record", "--ledger", self.ledger, "--agent", "forge"])
        self.assertEqual(code, 2)
        self.assertIn("--tool", err)

    def test_unknown_command_is_usage_error(self):
        code, _, _ = run(["frobnicate"])
        self.assertEqual(code, 2)


class TestVerify(CliTestCase):
    def test_clean_ledger_verifies(self):
        self.record()
        self.record()
        code, out, _ = run(["verify", "--ledger", self.ledger])
        self.assertEqual(code, 0)
        self.assertIn("OK", out)
        self.assertIn("2", out)

    def test_tampered_ledger_fails_with_exit_one(self):
        self.record()
        with open(self.ledger, "r", encoding="utf-8") as handle:
            text = handle.read()
        with open(self.ledger, "w", encoding="utf-8") as handle:
            handle.write(text.replace('"outcome":"ok"', '"outcome":"OK"'))
        code, out, _ = run(["verify", "--ledger", self.ledger])
        self.assertEqual(code, 1)
        self.assertIn("BREAK", out)

    def test_json_output_is_machine_readable(self):
        self.record()
        code, out, _ = run(["verify", "--ledger", self.ledger, "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["checked"], 1)

    def test_missing_ledger_is_usage_error_not_a_crash(self):
        code, _, err = run(["verify", "--ledger", os.path.join(self.dir, "absent.jsonl")])
        self.assertEqual(code, 2)
        self.assertIn("no such ledger", err)


class TestAudit(CliTestCase):
    def test_everything_unverified_trips_fail_on_flag(self):
        self.record()
        code, out, _ = run(["audit", "--ledger", self.ledger, "--fail-on", "flag"])
        self.assertEqual(code, 1)
        self.assertIn("AAL-001", out)
        self.assertIn("unverified", out)

    def test_fully_verified_passes(self):
        self.record(
            verifier="sentinel",
            model="deepseek/deepseek-v4.1",
            model_manifest=os.path.join(
                os.path.dirname(__file__), "data", "minilm.manifest.json"
            ),
            policy="p1",
        )
        code, out, _ = run(["audit", "--ledger", self.ledger, "--fail-on", "warn"])
        self.assertEqual(code, 0)
        self.assertIn("PASS", out)

    def test_a_typed_digest_no_longer_passes_fail_on_warn(self):
        self.record(
            verifier="sentinel",
            model="deepseek/deepseek-v4.1",
            model_digest="sha256:x",
            policy="p1",
        )
        code, out, _ = run(["audit", "--ledger", self.ledger, "--fail-on", "warn"])
        self.assertEqual(code, 1)
        self.assertIn("AAL-007", out)

    def test_json_audit_reports_counts(self):
        self.record()
        code, out, _ = run(["audit", "--ledger", self.ledger, "--json"])
        payload = json.loads(out)
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["unverified"], 1)
        self.assertIn("findings", payload)
        self.assertEqual(code, 1)

    def test_fail_on_none_never_fails_on_findings(self):
        self.record()
        code, _, _ = run(["audit", "--ledger", self.ledger, "--fail-on", "none"])
        self.assertEqual(code, 0)


class TestExport(CliTestCase):
    def test_export_then_verify_bundle(self):
        self.record()
        self.record()
        bundle = os.path.join(self.dir, "audit.bundle.json")
        code, _, _ = run(["export", "--ledger", self.ledger, "--out", bundle])
        self.assertEqual(code, 0)
        code, out, _ = run(["verify-bundle", bundle])
        self.assertEqual(code, 0)
        self.assertIn("OK", out)

    def test_tampered_bundle_fails(self):
        self.record(args_text="payload")
        bundle = os.path.join(self.dir, "audit.bundle.json")
        run(["export", "--ledger", self.ledger, "--out", bundle])
        with open(bundle, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        payload["entries"][0]["record"]["outcome"] = "FORGED"
        with open(bundle, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
        code, out, _ = run(["verify-bundle", bundle])
        self.assertEqual(code, 1)
        self.assertIn("BREAK", out)

    def test_missing_bundle_is_usage_error(self):
        code, _, err = run(["verify-bundle", os.path.join(self.dir, "absent.json")])
        self.assertEqual(code, 2)
        self.assertIn("no such bundle", err)


class TestTail(CliTestCase):
    def test_tail_prints_last_n(self):
        for i in range(4):
            self.record(data="arg%d" % i)
        code, out, _ = run(["tail", "--ledger", self.ledger, "-n", "2"])
        self.assertEqual(code, 0)
        self.assertEqual(len([line for line in out.splitlines() if line.strip()]), 2)
        self.assertIn("arg3", out)
        self.assertNotIn("arg0", out)


if __name__ == "__main__":
    unittest.main()
