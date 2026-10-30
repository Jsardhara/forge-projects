"""The cross-file signal: a backup that still holds the LIVE value.

This is the difference between "there is a key in a backup" (mild) and
"rotating .env will leave a working copy of the same key on disk" (the whole
point of a rotation that quietly did not finish).
"""
import tempfile
import unittest
from pathlib import Path

from secretsurface.scan import scan


def akia():
    return "AKIA" + "Q7FZ2M4XB9PLR3TK"


def gh_token():
    return "ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"


class DuplicateOfLiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, content):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def signals_for(self, report, rel):
        target = str(self.root / rel)
        found = [f for f in report.findings if f.path == target]
        self.assertEqual(len(found), 1, found)
        return found[0].signals

    def test_backup_holding_the_live_value_is_flagged(self):
        self.write("p/.env", "K=" + akia() + "\n")
        self.write("p/.env.bak.si09", "K=" + akia() + "\n")
        report = scan([self.root])
        self.assertIn("duplicate-of-live-env",
                      self.signals_for(report, "p/.env.bak.si09"))

    def test_backup_holding_a_different_value_is_not_flagged_duplicate(self):
        self.write("p/.env", "K=" + akia() + "\n")
        self.write("p/.env.bak.si09", "K=" + gh_token() + "\n")
        report = scan([self.root])
        self.assertNotIn("duplicate-of-live-env",
                         self.signals_for(report, "p/.env.bak.si09"))

    def test_the_live_env_itself_is_not_called_a_duplicate(self):
        self.write("p/.env", "K=" + akia() + "\n")
        self.write("p/.env.bak.si09", "K=" + akia() + "\n")
        report = scan([self.root])
        self.assertNotIn("duplicate-of-live-env",
                         self.signals_for(report, "p/.env"))

    def test_curator_blob_holding_the_live_value_is_flagged(self):
        self.write("p/.env", "K=" + akia() + "\n")
        self.write("p/.curator_backups/blobs/ab12", "K=" + akia() + "\n")
        report = scan([self.root])
        self.assertIn("duplicate-of-live-env",
                      self.signals_for(report, "p/.curator_backups/blobs/ab12"))

    def test_a_backup_with_no_live_twin_is_untouched(self):
        self.write("p/.env", "K=" + akia() + "\n")
        self.write("p/.env.bak.si09", "K=" + gh_token() + "\n")
        report = scan([self.root])
        signals = self.signals_for(report, "p/.env.bak.si09")
        self.assertIn("superseded-key-may-still-validate", signals)


if __name__ == "__main__":
    unittest.main()
