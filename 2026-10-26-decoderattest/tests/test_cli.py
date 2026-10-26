import io
import json
import os
import unittest

from decoderattest.cli import main
from support import FakeResult, FakeRunner, TmpTree, make_vendored_tree, rule_doc, write


def host_runner(node_version="v26.8.2", lib_version="1.2.0-3build1"):
    return FakeRunner(
        [
            (("which", "-a", "node"), FakeResult(0, "/usr/bin/node\n", "")),
            (("/usr/bin/node", "--version"), FakeResult(0, node_version + "\n", "")),
            (("which", "-a", "python3"), FakeResult(1, "", "")),
            (
                ("dpkg-query", "-W"),
                FakeResult(0, "libbrotli1\t%s\n" % lib_version, ""),
            ),
        ]
    )


def run(argv, runner, rules_path=None):
    out = io.StringIO()
    if rules_path is None:
        code = main(argv, runner=runner, out=out)
    else:
        code = main(argv + ["--rules", rules_path], runner=runner, out=out)
    return code, out.getvalue()


class CliTests(unittest.TestCase):
    def setUp(self):
        self.root = TmpTree().__enter__()
        self.rules = write(
            os.path.join(self.root, "rules.json"), json.dumps(rule_doc())
        )

    def test_exposed_host_exits_1_by_default(self):
        code, text = run(["--no-python"], host_runner(), self.rules)
        self.assertEqual(code, 1)
        self.assertIn("VERDICT: EXPOSED", text)

    def test_patched_host_exits_0(self):
        code, text = run(
            ["--no-python"], host_runner("v26.12.1", "1.2.1-1"), self.rules
        )
        self.assertEqual(code, 0)
        self.assertIn("VERDICT: CLEAN", text)

    def test_fail_on_never_always_exits_0(self):
        code, _ = run(
            ["--no-python", "--fail-on", "never"], host_runner(), self.rules
        )
        self.assertEqual(code, 0)

    def test_json_flag_emits_parseable_document(self):
        code, text = run(["--no-python", "--json"], host_runner(), self.rules)
        payload = json.loads(text)
        self.assertEqual(payload["verdict"], "EXPOSED")
        self.assertEqual(code, 1)

    def test_vendor_scan_is_included(self):
        tree = os.path.join(self.root, "project")
        make_vendored_tree(tree, version=(1, 2, 0), patched=False)
        code, text = run(
            ["--no-node", "--no-python", "--no-system", "--scan-vendor", tree],
            host_runner(),
            self.rules,
        )
        self.assertIn("decode.h", text)
        self.assertEqual(code, 1)

    def test_missing_vendor_path_is_exit_2_and_loud(self):
        code, text = run(
            ["--no-node", "--no-python", "--no-system", "--scan-vendor",
             os.path.join(self.root, "nope")],
            host_runner(),
            self.rules,
        )
        self.assertEqual(code, 2)
        self.assertIn("nope", text)

    def test_missing_rules_file_is_exit_2(self):
        out = io.StringIO()
        code = main(
            ["--rules", os.path.join(self.root, "missing.json"), "--no-python"],
            runner=host_runner(),
            out=out,
        )
        self.assertEqual(code, 2)
        self.assertIn("rules", out.getvalue().lower())

    def test_node_only_run_does_not_probe_python(self):
        runner = host_runner()
        code, _ = run(["--no-python", "--no-system"], runner, self.rules)
        self.assertEqual(code, 1)
        self.assertFalse(any("python" in " ".join(call) for call in runner.calls))


if __name__ == "__main__":
    unittest.main()
