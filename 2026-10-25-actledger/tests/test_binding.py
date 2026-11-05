"""Binding a measured model digest to a ledger row.

The failing test comes first: `actledger.manifest` did not exist when this file was
written, so every case below started RED with an ImportError.

The load-bearing assertion is `test_real_manifest_digest_matches_wsaudit`: the fixture
in `tests/data/minilm.manifest.json` was produced by `wsaudit hash --manifest-out` over
a real 90 MB safetensors file, and `model_digest` in it is wsaudit's own output. If our
recomputation matches that value, two independent implementations agree on the format.
"""

import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest

from actledger.cli import main
from actledger.manifest import (
    DIGEST_TAG,
    BindingError,
    ManifestError,
    bare_hex,
    canonical_digest,
    derive,
    is_tagged,
    load_bindings,
    load_manifest,
)

DATA = os.path.join(os.path.dirname(__file__), "data")
REAL_MANIFEST = os.path.join(DATA, "minilm.manifest.json")


def run(argv):
    out = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


def tensor(sha="a" * 64, dtype="F32", shape=(2, 3)):
    return {"dtype": dtype, "shape": list(shape), "sha256": sha}


def manifest(tensors=None, digest=None, partial=False, tool="wsaudit"):
    tensors = {"w": tensor()} if tensors is None else tensors
    return {
        "tool": tool,
        "version": 1,
        "format": "safetensors",
        "model_digest": canonical_digest(tensors, partial=partial) if digest is None else digest,
        "partial": partial,
        "tensor_count": len(tensors),
        "total_bytes": 24,
        "tensors": tensors,
    }


class TempCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="actledger-bind-")
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.ledger = os.path.join(self.dir, "actions.jsonl")

    def write_json(self, name, payload):
        path = os.path.join(self.dir, name)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        return path

    def write_raw(self, name, text):
        path = os.path.join(self.dir, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path


# --------------------------------------------------------------------------- manifest


class TestCanonicalDigest(unittest.TestCase):
    def test_real_manifest_digest_matches_wsaudit(self):
        payload = load_manifest(REAL_MANIFEST)
        self.assertEqual(len(payload["tensors"]), 106)
        self.assertEqual(canonical_digest(payload["tensors"]), payload["model_digest"])

    def test_order_of_tensors_does_not_change_the_digest(self):
        a = {"one": tensor("1" * 64), "two": tensor("2" * 64, "F16", (4,))}
        b = {"two": tensor("2" * 64, "F16", (4,)), "one": tensor("1" * 64)}
        self.assertEqual(canonical_digest(a), canonical_digest(b))

    def test_a_changed_tensor_hash_changes_the_digest(self):
        a = {"w": tensor("a" * 64)}
        b = {"w": tensor("b" * 64)}
        self.assertNotEqual(canonical_digest(a), canonical_digest(b))

    def test_a_changed_shape_changes_the_digest(self):
        a = {"w": tensor(shape=(2, 3))}
        b = {"w": tensor(shape=(3, 2))}
        self.assertNotEqual(canonical_digest(a), canonical_digest(b))

    def test_length_prefix_stops_a_boundary_collision(self):
        # ('a|b', 'cc') and ('a', 'bb|cc') concatenate identically without the lengths.
        left = {"a|b": tensor("c" * 64, "cc", ())}
        right = {"a": tensor("b" * 64, "b|cc", ())}
        self.assertNotEqual(canonical_digest(left), canonical_digest(right))

    def test_partial_and_full_differ(self):
        tensors = {"w": tensor()}
        self.assertNotEqual(
            canonical_digest(tensors, partial=True), canonical_digest(tensors, partial=False)
        )

    def test_digest_is_lowercase_hex_of_64(self):
        value = canonical_digest({"w": tensor()})
        self.assertRegex(value, r"^[0-9a-f]{64}$")


class TestLoadManifest(TempCase):
    def test_loads_the_real_manifest(self):
        payload = load_manifest(REAL_MANIFEST)
        self.assertEqual(payload["tool"], "wsaudit")
        self.assertEqual(payload["format"], "safetensors")
        self.assertFalse(payload["partial"])

    def test_missing_file_is_a_manifest_error(self):
        with self.assertRaises(ManifestError):
            load_manifest(os.path.join(self.dir, "nope.json"))

    def test_invalid_json_is_a_manifest_error(self):
        path = self.write_raw("bad.json", "{not json")
        with self.assertRaises(ManifestError):
            load_manifest(path)

    def test_non_object_is_a_manifest_error(self):
        path = self.write_json("list.json", [1, 2, 3])
        with self.assertRaises(ManifestError):
            load_manifest(path)

    def test_missing_key_names_the_key(self):
        payload = manifest()
        del payload["model_digest"]
        path = self.write_json("m.json", payload)
        with self.assertRaises(ManifestError) as ctx:
            load_manifest(path)
        self.assertIn("model_digest", str(ctx.exception))

    def test_foreign_tool_is_refused(self):
        path = self.write_json("m.json", manifest(tool="somethingelse"))
        with self.assertRaises(ManifestError) as ctx:
            load_manifest(path)
        self.assertIn("somethingelse", str(ctx.exception))

    def test_tensors_must_be_an_object(self):
        payload = manifest()
        payload["tensors"] = [{"name": "w"}]
        path = self.write_json("m.json", payload)
        with self.assertRaises(ManifestError):
            load_manifest(path)

    def test_short_sha_is_refused(self):
        payload = manifest(digest="a" * 64)
        payload["tensors"] = {"w": tensor("nothex")}
        path = self.write_json("m.json", payload)
        with self.assertRaises(ManifestError) as ctx:
            load_manifest(path)
        self.assertIn("sha256", str(ctx.exception))

    def test_shape_must_be_a_list_of_ints(self):
        payload = manifest(digest="a" * 64)
        payload["tensors"] = {"w": {"dtype": "F32", "shape": ["two"], "sha256": "a" * 64}}
        path = self.write_json("m.json", payload)
        with self.assertRaises(ManifestError):
            load_manifest(path)


class TestDerive(TempCase):
    def test_derive_recomputes_and_agrees_with_the_real_manifest(self):
        derived = derive(REAL_MANIFEST)
        self.assertEqual(derived.digest, load_manifest(REAL_MANIFEST)["model_digest"])
        self.assertEqual(derived.tagged, DIGEST_TAG + derived.digest)
        self.assertEqual(derived.tensor_count, 106)
        self.assertEqual(derived.format, "safetensors")
        self.assertRegex(derived.manifest_sha256, r"^[0-9a-f]{64}$")

    def test_partial_manifest_is_refused(self):
        path = self.write_json("m.json", manifest(partial=True))
        with self.assertRaises(ManifestError) as ctx:
            derive(path)
        self.assertIn("partial", str(ctx.exception))

    def test_internally_inconsistent_manifest_is_refused(self):
        path = self.write_json("m.json", manifest(digest="0" * 64))
        with self.assertRaises(ManifestError) as ctx:
            derive(path)
        self.assertIn("inconsistent", str(ctx.exception))

    def test_empty_tensor_list_is_refused(self):
        path = self.write_json("m.json", {"tool": "wsaudit", "format": "gguf",
                                          "model_digest": canonical_digest({}),
                                          "partial": False, "tensors": {}})
        with self.assertRaises(ManifestError):
            derive(path)


class TestTag(unittest.TestCase):
    def test_is_tagged(self):
        self.assertTrue(is_tagged("ws1:" + "a" * 64))
        self.assertFalse(is_tagged("a" * 64))
        self.assertFalse(is_tagged("ws1:zz"))

    def test_bare_hex_strips_the_tag(self):
        self.assertEqual(bare_hex("ws1:" + "A" * 64), "a" * 64)
        self.assertEqual(bare_hex("a" * 64), "a" * 64)
        self.assertIsNone(bare_hex("deadbeef"))
        self.assertIsNone(bare_hex(""))


# ------------------------------------------------------------------------------- CLI


class CliCase(TempCase):
    def record(self, *extra, agent="forge", tool="file.read"):
        argv = ["record", "--ledger", self.ledger, "--agent", agent,
                "--tool", tool, "--outcome", "ok", "--verifier", "sentinel",
                "--policy", "pol-7"]
        argv.extend(extra)
        return run(argv)

    def audit(self, *extra):
        return run(["audit", "--ledger", self.ledger] + list(extra))

    def sidecar(self):
        return self.ledger + ".manifests.jsonl"

    def entries(self):
        with open(self.ledger, "r", encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]


class TestRecordWithManifest(CliCase):
    def test_record_derives_the_digest_from_the_manifest(self):
        code, out, err = self.record("--model", "minilm", "--model-manifest", REAL_MANIFEST)
        self.assertEqual(code, 0, err)
        entry = self.entries()[0]["record"]
        self.assertEqual(entry["model_digest"], DIGEST_TAG + derive(REAL_MANIFEST).digest)
        self.assertEqual(entry["model_id"], "minilm")

    def test_agreeing_free_form_digest_is_accepted(self):
        digest = derive(REAL_MANIFEST).digest
        code, _, err = self.record("--model", "minilm", "--model-manifest", REAL_MANIFEST,
                                   "--model-digest", digest)
        self.assertEqual(code, 0, err)

    def test_conflicting_free_form_digest_fails_closed_and_writes_nothing(self):
        code, out, err = self.record("--model", "minilm", "--model-manifest", REAL_MANIFEST,
                                     "--model-digest", "b" * 64)
        self.assertEqual(code, 2)
        self.assertIn("disagree", err)
        self.assertFalse(os.path.exists(self.ledger))
        self.assertFalse(os.path.exists(self.sidecar()))

    def test_manifest_without_model_id_is_refused(self):
        code, _, err = self.record("--model-manifest", REAL_MANIFEST)
        self.assertEqual(code, 2)
        self.assertIn("--model", err)
        self.assertFalse(os.path.exists(self.ledger))

    def test_partial_manifest_writes_nothing(self):
        path = self.write_json("m.json", manifest(partial=True))
        code, _, err = self.record("--model", "m", "--model-manifest", path)
        self.assertEqual(code, 2)
        self.assertIn("partial", err)
        self.assertFalse(os.path.exists(self.ledger))

    def test_binding_is_recorded_beside_the_ledger(self):
        self.record("--model", "minilm", "--model-manifest", REAL_MANIFEST)
        with open(self.sidecar(), "r", encoding="utf-8") as fh:
            lines = [json.loads(line) for line in fh if line.strip()]
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["seq"], 0)
        self.assertEqual(lines[0]["model_digest"], DIGEST_TAG + derive(REAL_MANIFEST).digest)
        self.assertEqual(lines[0]["tensor_count"], 106)
        self.assertEqual(lines[0]["format"], "safetensors")


class TestAuditProvenance(CliCase):
    def test_free_form_digest_is_reported_unmeasured(self):
        self.record("--model", "minilm", "--model-digest", "abcdef")
        code, out, _ = self.audit()
        self.assertIn("AAL-007", out)
        self.assertIn("UNMEASURED", out)
        # WARN sits below the default --fail-on FLAG gate: reported, not fatal.
        self.assertEqual(code, 0)
        code, out, _ = self.audit("--fail-on", "warn")
        self.assertEqual(code, 1)

    def test_a_hand_typed_measured_tag_is_not_evidence(self):
        self.record("--model", "minilm", "--model-digest", DIGEST_TAG + "c" * 64)
        code, out, _ = self.audit()
        self.assertIn("AAL-007", out)

    def test_bound_row_is_measured(self):
        self.record("--model", "minilm", "--model-manifest", REAL_MANIFEST)
        code, out, _ = self.audit()
        self.assertNotIn("AAL-007", out)
        self.assertIn("verdict: PASS", out)
        self.assertEqual(code, 0)

    def test_binding_for_a_different_digest_does_not_count(self):
        self.record("--model", "minilm", "--model-manifest", REAL_MANIFEST)
        path = self.write_raw(self.sidecar(), json.dumps(
            {"seq": 0, "model_digest": DIGEST_TAG + "d" * 64, "tensor_count": 1}
        ) + "\n")
        code, out, _ = self.audit()
        self.assertIn("AAL-007", out)

    def test_malformed_binding_file_is_exit_2_not_a_silent_pass(self):
        self.record("--model", "minilm", "--model-manifest", REAL_MANIFEST)
        self.write_raw(self.sidecar(), "this is not json\n")
        code, out, err = self.audit()
        self.assertEqual(code, 2)
        self.assertIn("binding", err.lower())

    def test_json_output_carries_the_code(self):
        self.record("--model", "minilm", "--model-digest", "abcdef")
        code, out, _ = self.audit("--json")
        payload = json.loads(out)
        codes = [f["code"] for f in payload["findings"]]
        self.assertIn("AAL-007", codes)
        self.assertEqual(payload["severity"], "WARN")

    def test_measured_row_still_flags_a_missing_model_id(self):
        self.record("--model-digest", DIGEST_TAG + "e" * 64)
        code, out, _ = self.audit()
        self.assertIn("AAL-004", out)


class TestLoadManifestRejects(TempCase):
    """Every shape defect must be loud: a silently-accepted manifest is a false pass."""

    def reject(self, payload, fragment):
        path = self.write_json("m.json", payload)
        with self.assertRaises(ManifestError) as ctx:
            load_manifest(path)
        self.assertIn(fragment, str(ctx.exception))

    def test_tensor_entry_not_an_object(self):
        payload = manifest(digest="a" * 64)
        payload["tensors"] = {"w": "not-an-object"}
        self.reject(payload, "not an object")

    def test_tensor_without_dtype(self):
        payload = manifest(digest="a" * 64)
        payload["tensors"] = {"w": {"shape": [], "sha256": "a" * 64}}
        self.reject(payload, "dtype")

    def test_unknown_format(self):
        payload = manifest(digest="a" * 64)
        payload["format"] = "pytorch-bin"
        self.reject(payload, "pytorch-bin")

    def test_model_digest_not_hex(self):
        payload = manifest(digest="sha256:deadbeef")
        self.reject(payload, "model_digest")

    def test_partial_not_boolean(self):
        payload = manifest(digest="a" * 64)
        payload["partial"] = "no"
        self.reject(payload, "boolean")


class TestBindingFile(TempCase):
    def write_binding(self, text):
        self.write_raw(self.ledger + ".manifests.jsonl", text)
        return load_bindings(self.ledger)

    def test_absent_file_means_nothing_bound(self):
        self.assertEqual(load_bindings(self.ledger), {})

    def test_blank_lines_are_skipped(self):
        bindings = self.write_binding(
            "\n" + json.dumps({"seq": 0, "model_digest": DIGEST_TAG + "a" * 64}) + "\n\n"
        )
        self.assertEqual(bindings, {0: DIGEST_TAG + "a" * 64})

    def test_a_line_that_is_not_a_binding_record_is_loud(self):
        with self.assertRaises(BindingError) as ctx:
            self.write_binding(json.dumps({"seq": 0}) + "\n")
        self.assertIn("binding record", str(ctx.exception))

    def test_a_non_integer_seq_is_loud(self):
        with self.assertRaises(BindingError) as ctx:
            self.write_binding(json.dumps({"seq": "zero", "model_digest": "x"}) + "\n")
        self.assertIn("non-integer", str(ctx.exception))

    def test_a_duplicate_seq_is_loud(self):
        line = json.dumps({"seq": 0, "model_digest": DIGEST_TAG + "a" * 64}) + "\n"
        with self.assertRaises(BindingError) as ctx:
            self.write_binding(line + line)
        self.assertIn("twice", str(ctx.exception))


class TestVerifyBinding(CliCase):
    def test_reports_bound_rows(self):
        self.record("--model", "minilm", "--model-manifest", REAL_MANIFEST)
        self.record("--model", "minilm", "--model-manifest", REAL_MANIFEST)
        code, out, _ = run(["verify-binding", "--ledger", self.ledger,
                            "--manifest", REAL_MANIFEST])
        self.assertEqual(code, 0)
        self.assertIn("2 action(s)", out)

    def test_no_bound_rows_is_exit_1(self):
        self.record("--model", "other", "--model-digest", "f" * 64)
        code, out, _ = run(["verify-binding", "--ledger", self.ledger,
                            "--manifest", REAL_MANIFEST])
        self.assertEqual(code, 1)
        self.assertIn("0 action(s)", out)

    def test_missing_ledger_is_exit_2(self):
        code, _, err = run(["verify-binding", "--ledger", os.path.join(self.dir, "none.jsonl"),
                            "--manifest", REAL_MANIFEST])
        self.assertEqual(code, 2)
        self.assertIn("error", err)

    def test_json_shape(self):
        self.record("--model", "minilm", "--model-manifest", REAL_MANIFEST)
        code, out, _ = run(["verify-binding", "--ledger", self.ledger,
                            "--manifest", REAL_MANIFEST, "--json"])
        payload = json.loads(out)
        self.assertEqual(payload["bound"], 1)
        self.assertEqual(payload["model_digest"], derive(REAL_MANIFEST).tagged)
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
