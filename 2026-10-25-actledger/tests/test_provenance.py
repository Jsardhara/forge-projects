"""Provenance of the manifest a digest came from.

Written before the implementation: `actledger.provenance` did not exist when this file
was written, so every case below started RED with an ImportError.

The defect these tests pin: `append_binding` records `format`, `tensor_count`,
`manifest_sha256` and `manifest` (an abspath) beside the ledger, and nothing ever read
them back. `audit` asked only "does a binding name this digest" - so a MEASURED row
carried four claims whose truth nothing checked, and a ledger moved to another machine
recorded paths that mean nothing there.

States are three, never two: PASS (recomputed fingerprint matches), MISMATCH (it does
not), UNMEASURABLE (the file is gone or unreadable - which is NOT a pass).
"""

import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest

from actledger.cli import main
from actledger.manifest import DIGEST_TAG, canonical_digest, load_binding_records
from actledger.provenance import MISMATCH, PASS, UNMEASURABLE, check_bindings


def run(argv):
    out = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


def tensor(sha="a" * 64, dtype="F32", shape=(2, 3)):
    return {"dtype": dtype, "shape": list(shape), "sha256": sha}


def manifest(tensors=None, known_digest=True):
    tensors = {"w": tensor()} if tensors is None else tensors
    payload = {
        "tool": "wsaudit",
        "version": 1,
        "format": "safetensors",
        "model_digest": canonical_digest(tensors) if known_digest else "0" * 64,
        "partial": False,
        "tensor_count": len(tensors),
        "total_bytes": 24,
        "tensors": tensors,
    }
    return payload


class TempCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="actledger-prov-")
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.ledger = os.path.join(self.dir, "actions.jsonl")

    def write_json(self, name, payload, directory=None):
        path = os.path.join(directory or self.dir, name)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
        return path

    def write_raw(self, name, text, directory=None):
        path = os.path.join(directory or self.dir, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def record(self, manifest_path, ledger=None, model="minilm", tool="read_file"):
        argv = [
            "record",
            "--ledger", ledger or self.ledger,
            "--agent", "forge",
            "--tool", tool,
            "--outcome", "ok",
            "--model", model,
            "--verifier", "sentinel",
            "--policy", "p1",
            "--model-manifest", manifest_path,
        ]
        code, out, err = run(argv)
        self.assertEqual(code, 0, err)
        return out

    def bindings(self, ledger=None):
        return load_binding_records(ledger or self.ledger)

    def entries_of(self, ledger=None):
        from actledger.ledger import Ledger

        return Ledger(ledger or self.ledger).entries()


# ------------------------------------------------------------------- clean roundtrip


class TestCleanRoundtrip(TempCase):
    def test_an_untouched_manifest_is_a_pass(self):
        path = self.write_json("minilm.manifest.json", manifest())
        self.record(path)

        report = check_bindings(self.entries_of(), self.bindings(), self.ledger)

        self.assertEqual(report.checked, 1)
        self.assertEqual(report.passed, 1)
        self.assertEqual(report.mismatched, 0)
        self.assertEqual(report.unmeasurable, 0)
        self.assertEqual(report.checks[0].state, PASS)
        self.assertEqual(report.findings, ())

    def test_the_check_ok_reports_which_file_it_actually_read(self):
        path = self.write_json("minilm.manifest.json", manifest())
        self.record(path)

        report = check_bindings(self.entries_of(), self.bindings(), self.ledger)

        self.assertEqual(report.checks[0].manifest, os.path.abspath(path))
        self.assertEqual(report.checks[0].resolved_by, "path")

    def test_cli_audit_verify_manifest_is_clean(self):
        path = self.write_json("minilm.manifest.json", manifest())
        self.record(path)

        code, out, _ = run(["audit", "--ledger", self.ledger, "--verify-manifest"])

        self.assertEqual(code, 0)
        self.assertIn("provenance: 1 checked", out)
        self.assertIn("1 pass", out)
        self.assertEqual(out.count("MANIFEST-SHA-MISMATCH"), 0)

    def test_json_output_carries_the_provenance_block(self):
        path = self.write_json("minilm.manifest.json", manifest())
        self.record(path)

        code, out, _ = run(["audit", "--ledger", self.ledger, "--verify-manifest", "--json"])

        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["provenance"]["checked"], 1)
        self.assertEqual(payload["provenance"]["passed"], 1)
        self.assertEqual(payload["provenance"]["mismatched"], 0)
        self.assertEqual(payload["severity"], "PASS")


# ------------------------------------------------------------------------ mismatch


class TestMismatch(TempCase):
    def test_a_manifest_edited_after_binding_is_a_mismatch(self):
        path = self.write_json("minilm.manifest.json", manifest())
        self.record(path)
        # Same shape, same digest claim, different tensor bytes: only the fingerprint moves.
        self.write_json("minilm.manifest.json", manifest({"w": tensor("b" * 64)}))

        report = check_bindings(self.entries_of(), self.bindings(), self.ledger)

        self.assertEqual(report.checked, 1)
        self.assertEqual(report.mismatched, 1)
        self.assertEqual(report.checks[0].state, MISMATCH)
        self.assertEqual([finding.code for finding in report.findings],
                         ["MANIFEST-SHA-MISMATCH"])

    def test_any_edit_is_caught_even_when_the_tensors_are_untouched(self):
        path = self.write_json("minilm.manifest.json", manifest())
        self.record(path)
        payload = manifest()
        payload["total_bytes"] = 25
        self.write_json("minilm.manifest.json", payload)

        report = check_bindings(self.entries_of(), self.bindings(), self.ledger)

        self.assertEqual(report.checks[0].state, MISMATCH)

    def test_cli_exit_is_1_on_a_mismatch(self):
        path = self.write_json("minilm.manifest.json", manifest())
        self.record(path)
        self.write_json("minilm.manifest.json", manifest({"w": tensor("b" * 64)}))

        code, out, _ = run(["audit", "--ledger", self.ledger, "--verify-manifest"])

        self.assertEqual(code, 1)
        self.assertIn("MANIFEST-SHA-MISMATCH", out)
        self.assertIn("1 mismatch", out)

    def test_the_mismatch_names_the_row_and_both_fingerprints(self):
        path = self.write_json("minilm.manifest.json", manifest())
        self.record(path)
        self.write_json("minilm.manifest.json", manifest({"w": tensor("b" * 64)}))

        report = check_bindings(self.entries_of(), self.bindings(), self.ledger)
        detail = report.findings[0].detail

        self.assertIn("seq 0", detail)
        self.assertIn("recorded", detail)
        self.assertIn("now", detail)


# -------------------------------------------------------------------- unmeasurable


class TestUnmeasurable(TempCase):
    def test_a_deleted_manifest_is_unmeasurable_not_a_pass(self):
        path = self.write_json("minilm.manifest.json", manifest())
        self.record(path)
        os.remove(path)

        report = check_bindings(self.entries_of(), self.bindings(), self.ledger)

        self.assertEqual(report.checked, 1)
        self.assertEqual(report.passed, 0)
        self.assertEqual(report.unmeasurable, 1)
        self.assertEqual(report.checks[0].state, UNMEASURABLE)
        self.assertEqual([finding.code for finding in report.findings],
                         ["MANIFEST-UNMEASURABLE"])

    def test_the_verdict_warn_is_visible_even_when_the_default_gate_passes(self):
        path = self.write_json("minilm.manifest.json", manifest())
        self.record(path)
        os.remove(path)

        code, out, _ = run(["audit", "--ledger", self.ledger, "--verify-manifest"])

        self.assertEqual(code, 0)  # default --fail-on FLAG: WARN is reported, not fatal
        self.assertIn("verdict: WARN", out)
        self.assertIn("MANIFEST-UNMEASURABLE", out)

    def test_fail_on_warn_turns_unmeasurable_into_a_failure(self):
        path = self.write_json("minilm.manifest.json", manifest())
        self.record(path)
        os.remove(path)

        code, out, _ = run(
            ["audit", "--ledger", self.ledger, "--verify-manifest", "--fail-on", "warn"]
        )

        self.assertEqual(code, 1)

    def test_a_manifest_that_is_no_longer_json_is_unmeasurable(self):
        path = self.write_json("minilm.manifest.json", manifest())
        self.record(path)
        self.write_raw("minilm.manifest.json", "{not json at all")

        report = check_bindings(self.entries_of(), self.bindings(), self.ledger)

        self.assertEqual(report.checks[0].state, UNMEASURABLE)

    def test_a_binding_written_before_provenance_was_tracked_is_unmeasurable(self):
        path = self.write_json("minilm.manifest.json", manifest())
        self.record(path)
        sidecar = self.ledger + ".manifests.jsonl"
        with open(sidecar, "r", encoding="utf-8") as handle:
            full = json.loads(handle.readline())
        # A line written before this change: digest only, no fingerprint taken.
        self.write_raw(
            "actions.jsonl.manifests.jsonl",
            json.dumps({"seq": full["seq"], "model_digest": full["model_digest"]}) + "\n",
        )

        report = check_bindings(self.entries_of(), self.bindings(), self.ledger)

        self.assertEqual(report.checked, 1)
        self.assertEqual(report.checks[0].state, UNMEASURABLE)
        self.assertIn("manifest_sha256", report.checks[0].detail)


# ---------------------------------------------------------------------- portability


class TestPortability(TempCase):
    def test_the_binding_records_the_basename_as_well_as_the_abspath(self):
        path = self.write_json("minilm.manifest.json", manifest())
        self.record(path)

        with open(self.ledger + ".manifests.jsonl", "r", encoding="utf-8") as handle:
            line = json.loads(handle.readline())

        self.assertEqual(line["manifest"], os.path.abspath(path))
        self.assertEqual(line["manifest_basename"], "minilm.manifest.json")

    def test_a_ledger_moved_with_its_manifest_still_verifies_by_name(self):
        source = tempfile.mkdtemp(prefix="actledger-src-")
        self.addCleanup(shutil.rmtree, source, True)
        path = self.write_json("minilm.manifest.json", manifest(), directory=source)
        ledger = os.path.join(source, "actions.jsonl")
        self.record(path, ledger=ledger)

        moved = tempfile.mkdtemp(prefix="actledger-dst-")
        self.addCleanup(shutil.rmtree, moved, True)
        for name in ("actions.jsonl", "actions.jsonl.manifests.jsonl", "minilm.manifest.json"):
            shutil.copy2(os.path.join(source, name), os.path.join(moved, name))
        # The machine the ledger was written on is gone.
        shutil.rmtree(source, True)

        moved_ledger = os.path.join(moved, "actions.jsonl")
        report = check_bindings(
            self.entries_of(moved_ledger), self.bindings(moved_ledger), moved_ledger
        )

        self.assertEqual(report.checks[0].state, PASS)
        self.assertEqual(report.checks[0].resolved_by, "basename")

    def test_a_renamed_manifest_is_still_unmeasurable(self):
        path = self.write_json("minilm.manifest.json", manifest())
        self.record(path)
        os.rename(path, os.path.join(self.dir, "renamed.manifest.json"))

        report = check_bindings(self.entries_of(), self.bindings(), self.ledger)

        self.assertEqual(report.checks[0].state, UNMEASURABLE)


# ------------------------------------------------------------------------- scoping


class TestScoping(TempCase):
    def test_rows_with_no_binding_are_not_checked(self):
        path = self.write_json("minilm.manifest.json", manifest())
        self.record(path)
        run(
            [
                "record",
                "--ledger", self.ledger,
                "--agent", "forge",
                "--tool", "read_file",
                "--outcome", "ok",
                "--verifier", "sentinel",
                "--policy", "p1",
            ]
        )

        report = check_bindings(self.entries_of(), self.bindings(), self.ledger)

        self.assertEqual(report.checked, 1)
        self.assertEqual(len(report.checks), 1)

    def test_an_empty_ledger_checks_nothing(self):
        report = check_bindings((), {}, self.ledger)

        self.assertEqual(report.checked, 0)
        self.assertEqual(report.findings, ())

    def test_audit_without_the_flag_does_not_consult_the_manifest(self):
        path = self.write_json("minilm.manifest.json", manifest())
        self.record(path)
        os.remove(path)

        code, out, _ = run(["audit", "--ledger", self.ledger])

        self.assertEqual(code, 0)
        self.assertNotIn("provenance:", out)


if __name__ == "__main__":
    unittest.main()