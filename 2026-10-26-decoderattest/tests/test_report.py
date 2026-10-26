import json
import unittest

from decoderattest.attest import attest
from decoderattest.inventory import NodeInstall, PythonInstall, SystemPackage
from decoderattest.report import render_json, render_text, to_dict
from decoderattest.rules import RuleSet
from support import rule_doc


def exposed():
    return attest(
        RuleSet(rule_doc()),
        nodes=[NodeInstall("/usr/bin/node", "26.8.2", None)],
        pythons=[PythonInstall("/p/python3", "3.12.4", {"Brotli": {"version": "1.2.1"}}, None)],
        packages=[SystemPackage("libbrotli1", "1.2.0-3build1", "dpkg")],
        vendored=[],
    )


class TextTests(unittest.TestCase):
    def test_verdict_line_is_first_class(self):
        text = render_text(exposed())
        self.assertIn("VERDICT: EXPOSED", text)

    def test_every_target_appears_with_its_version(self):
        text = render_text(exposed())
        self.assertIn("/usr/bin/node", text)
        self.assertIn("26.8.2", text)
        self.assertIn("libbrotli1", text)
        self.assertIn("1.2.0-3build1", text)

    def test_counts_line(self):
        text = render_text(exposed())
        self.assertIn("affected 2", text)
        self.assertIn("patched 1", text)

    def test_remediation_is_printed_for_affected_targets(self):
        text = render_text(exposed())
        self.assertIn("26.12.1", text)
        self.assertIn("fix", text.lower())


class JsonTests(unittest.TestCase):
    def test_json_is_valid_and_stable(self):
        payload = json.loads(render_json(exposed()))
        self.assertEqual(payload["advisory"]["id"], "CVE-2099-0001")
        self.assertEqual(payload["verdict"], "EXPOSED")
        self.assertEqual(len(payload["findings"]), 3)
        target = payload["findings"][0]
        for key in ("ecosystem", "target", "version", "status", "severity", "reason"):
            self.assertIn(key, target)

    def test_to_dict_counts_match_findings(self):
        payload = to_dict(exposed())
        self.assertEqual(payload["counts"]["found"], len(payload["findings"]))

    def test_json_is_ascii_only(self):
        render_json(exposed()).encode("ascii")


if __name__ == "__main__":
    unittest.main()
