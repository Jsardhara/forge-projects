"""Runner: subprocess isolation, timeout, and fail-closed behaviour."""

import os
import tempfile
import unittest

from posture.discover import Verifier
from posture.models import CLEAN, ERROR, FINDINGS, UNMEASURABLE
from posture.runner import run_verifier
from posture.specs import VerifierSpec

# A fake verifier package that writes a chosen body and exits a chosen code.
FAKE_CLI = '''
import os, sys
sys.stdout.write(os.environ.get("FAKE_STDOUT", "ok\\n"))
sys.stderr.write(os.environ.get("FAKE_STDERR", ""))
sys.exit(int(os.environ.get("FAKE_EXIT", "0")))
'''

MAIN = (
    "import os, runpy\n"
    "runpy.run_path(os.path.join(os.path.dirname(__file__), 'cli.py'), run_name='__main__')\n"
)

SLEEPY_CLI = '''
import time
time.sleep(5)
'''

NOISY_MODULE_CLI = '''
raise RuntimeError("boom")
'''


class RunnerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def _verifier(self, source, name="alpha", executable=True):
        d = os.path.join(self.root, "2026-01-01-" + name)
        pkg = os.path.join(d, "src", name)
        os.makedirs(pkg)
        with open(os.path.join(pkg, "__init__.py"), "w") as fh:
            fh.write("")
        with open(os.path.join(pkg, "cli.py"), "w") as fh:
            fh.write(source)
        if executable:
            with open(os.path.join(pkg, "__main__.py"), "w") as fh:
                fh.write(MAIN)
        return Verifier(spec=VerifierSpec(name=name, module=name, path=d), spec_path=d)

    def test_exit_zero_is_clean(self):
        v = self._verifier(FAKE_CLI)
        res = run_verifier(v, env={"FAKE_EXIT": "0"}, timeout=10)
        self.assertEqual(res.status, CLEAN)
        self.assertEqual(res.exit_code, 0)

    def test_exit_one_is_findings(self):
        v = self._verifier(FAKE_CLI)
        res = run_verifier(v, env={"FAKE_EXIT": "1"}, timeout=10)
        self.assertEqual(res.status, FINDINGS)

    def test_exit_two_is_unmeasurable(self):
        v = self._verifier(FAKE_CLI)
        res = run_verifier(v, env={"FAKE_EXIT": "2"}, timeout=10)
        self.assertEqual(res.status, UNMEASURABLE)

    def test_unexpected_exit_is_error_not_clean(self):
        v = self._verifier(FAKE_CLI)
        res = run_verifier(v, env={"FAKE_EXIT": "9"}, timeout=10)
        self.assertEqual(res.status, ERROR)

    def test_traceback_exit_one_is_error(self):
        """A crash exiting 1 must not be read as a real finding."""
        v = self._verifier(NOISY_MODULE_CLI)
        res = run_verifier(v, timeout=10)
        self.assertEqual(res.status, ERROR)
        self.assertIn("Traceback", res.error or "")

    def test_timeout_is_error_and_bounded(self):
        v = self._verifier(SLEEPY_CLI)
        res = run_verifier(v, timeout=1)
        self.assertEqual(res.status, ERROR)
        self.assertIn("timeout", (res.error or "").lower())
        self.assertLess(res.duration_s, 4.0)

    def test_captures_stdout(self):
        v = self._verifier(FAKE_CLI)
        res = run_verifier(v, env={"FAKE_STDOUT": "hello\n"}, timeout=10)
        self.assertTrue(res.digest)

    def test_stdout_is_not_stored_verbatim(self):
        v = self._verifier(FAKE_CLI)
        res = run_verifier(v, env={"FAKE_STDOUT": "secret-ish-value\n"}, timeout=10)
        self.assertFalse(hasattr(res, "stdout"))
        self.assertEqual(len(res.digest), 16)

    def test_silent_exit_zero_is_unmeasurable(self):
        """A verifier that proved nothing must not read as clean."""
        v = self._verifier(FAKE_CLI)
        res = run_verifier(v, env={"FAKE_EXIT": "0", "FAKE_STDOUT": ""}, timeout=10)
        self.assertEqual(res.status, UNMEASURABLE)
        self.assertIn("no output", (res.error or "").lower())

    def test_missing_package_is_error_not_clean(self):
        d = os.path.join(self.root, "2026-01-01-ghost")
        os.makedirs(os.path.join(d, "src"))
        v = Verifier(
            spec=VerifierSpec(name="ghost", module="ghost", path=d), spec_path=d
        )
        res = run_verifier(v, timeout=10)
        self.assertEqual(res.status, ERROR)

    def test_package_without_main_is_error_not_findings(self):
        """A package Python cannot execute must never report as a real finding."""
        v = self._verifier(FAKE_CLI, executable=False)
        res = run_verifier(v, env={"FAKE_EXIT": "1"}, timeout=10)
        self.assertEqual(res.status, ERROR)

    def test_volatile_counter_does_not_change_digest(self):
        """Registered volatile patterns keep a changing block height quiet."""
        d = os.path.join(self.root, "2026-01-01-exitpath")
        pkg = os.path.join(d, "src", "exitpath")
        os.makedirs(pkg)
        open(os.path.join(pkg, "__init__.py"), "w").close()
        with open(os.path.join(pkg, "cli.py"), "w") as fh:
            fh.write(
                "import os, sys\n"
                "h = open(os.path.join(os.path.dirname(__file__), '../../h.txt')).read().strip()\n"
                "print('ethereum healthy block ' + h)\n"
                "sys.exit(1)\n"
            )
        with open(os.path.join(pkg, "__main__.py"), "w") as fh:
            fh.write(MAIN)
        v = Verifier(
            spec=VerifierSpec(name="exitpath", module="exitpath", path=d), spec_path=d
        )

        def run(height):
            with open(os.path.join(d, "h.txt"), "w") as fh:
                fh.write(height + "\n")
            return run_verifier(v, timeout=10)

        first = run("26332507")
        second = run("53449152")
        self.assertEqual(first.status, FINDINGS)
        self.assertEqual(first.digest, second.digest)

    def test_verifier_env_is_isolated_from_caller(self):
        """The parent's PYTHONPATH must not leak into the child unchanged."""
        v = self._verifier(FAKE_CLI)
        res = run_verifier(v, env={"FAKE_EXIT": "0", "PYTHONPATH": "/nope"}, timeout=10)
        self.assertEqual(res.status, CLEAN)


if __name__ == "__main__":
    unittest.main()
