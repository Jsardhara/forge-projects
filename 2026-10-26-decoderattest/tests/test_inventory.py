import json
import unittest

from decoderattest.inventory import (
    PROBE_SOURCE,
    discover_python_paths,
    find_node,
    find_pythons,
    find_system_packages,
    parse_debian_version_line,
)
from support import FakeResult, FakeRunner


class NodeTests(unittest.TestCase):
    def test_parses_version_and_strips_leading_v(self):
        runner = FakeRunner(
            [
                (("which", "-a"), FakeResult(0, "/usr/bin/node\n", "")),
                (("/usr/bin/node", "--version"), FakeResult(0, "v26.8.2\n", "")),
            ]
        )
        nodes = find_node(runner)
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].version, "26.8.2")
        self.assertEqual(nodes[0].path, "/usr/bin/node")

    def test_multiple_installs_are_all_reported(self):
        runner = FakeRunner(
            [
                (("which", "-a"), FakeResult(0, "/usr/bin/node\n/opt/n/node\n", "")),
                (("/usr/bin/node", "--version"), FakeResult(0, "v22.23.3\n", "")),
                (("/opt/n/node", "--version"), FakeResult(0, "v26.12.1\n", "")),
            ]
        )
        nodes = {n.path: n.version for n in find_node(runner)}
        self.assertEqual(nodes, {"/usr/bin/node": "22.23.3", "/opt/n/node": "26.12.1"})

    def test_missing_node_is_an_empty_list_not_an_error(self):
        runner = FakeRunner([(("which", "-a"), FakeResult(1, "", "no node"))])
        self.assertEqual(find_node(runner), [])

    def test_unparsable_version_is_recorded_as_error(self):
        runner = FakeRunner(
            [
                (("which", "-a"), FakeResult(0, "/usr/bin/node\n", "")),
                (("/usr/bin/node", "--version"), FakeResult(0, "garbage\n", "")),
            ]
        )
        nodes = find_node(runner)
        self.assertEqual(len(nodes), 1)
        self.assertIsNone(nodes[0].version)
        self.assertIn("unparsable", nodes[0].error)


class PythonTests(unittest.TestCase):
    def probe_payload(self):
        return json.dumps(
            {
                "executable": "/usr/bin/python3.14",
                "version": "3.14.7",
                "modules": {
                    "brotli": {"version": "1.2.0", "file": "/x/brotli.py"},
                    "brotlicffi": {"version": "1.2.1.0", "file": "/x/brotlicffi/__init__.py"},
                },
            }
        )

    def test_probe_is_run_as_a_separate_process_per_interpreter(self):
        runner = FakeRunner(
            [(("/usr/bin/python3.14", "-c"), FakeResult(0, self.probe_payload(), ""))]
        )
        installs = find_pythons(runner, ["/usr/bin/python3.14"])
        self.assertEqual(len(installs), 1)
        self.assertEqual(installs[0].version, "3.14.7")
        self.assertEqual(set(installs[0].modules), {"brotli", "brotlicffi"})
        self.assertEqual(runner.calls[0][1], "-c")
        self.assertEqual(runner.calls[0][2], PROBE_SOURCE)

    def test_failed_probe_is_recorded_loudly(self):
        runner = FakeRunner(
            [(("/usr/bin/python3.14", "-c"), FakeResult(1, "", "boom"))]
        )
        install = find_pythons(runner, ["/usr/bin/python3.14"])[0]
        self.assertIsNone(install.version)
        self.assertIn("boom", install.error)
        self.assertEqual(install.modules, {})

    def test_probe_output_that_is_not_json_is_an_error(self):
        runner = FakeRunner(
            [(("/usr/bin/python3.14", "-c"), FakeResult(0, "site-packages noise", ""))]
        )
        install = find_pythons(runner, ["/usr/bin/python3.14"])[0]
        self.assertIsNone(install.version)
        self.assertIn("probe", install.error)

    def test_probe_source_reports_metadata_fallback(self):
        # A module with no __version__ must still yield a version when metadata has one.
        self.assertIn("importlib.metadata", PROBE_SOURCE)
        self.assertIn("brotlicffi", PROBE_SOURCE)

    def test_discover_dedupes_and_keeps_order(self):
        runner = FakeRunner(
            [(("which", "-a", "python3"), FakeResult(0, "/a/python3\n/b/python3\n", ""))]
        )
        paths = discover_python_paths(runner, extras=["/b/python3", "/c/python3"])
        self.assertEqual(paths, ["/b/python3", "/c/python3", "/a/python3"])


class SystemPackageTests(unittest.TestCase):
    def test_dpkg_query_output_is_parsed(self):
        runner = FakeRunner(
            [
                (
                    ("dpkg-query", "-W"),
                    FakeResult(
                        0,
                        "libbrotli1\t1.2.0-3build1\nbrotli\t1.0.9-2\n",
                        "",
                    ),
                )
            ]
        )
        packages = find_system_packages(runner, ["libbrotli1", "brotli"])
        self.assertEqual(
            {p.name: p.version for p in packages},
            {"libbrotli1": "1.2.0-3build1", "brotli": "1.0.9-2"},
        )
        self.assertEqual(packages[0].manager, "dpkg")

    def test_absent_package_is_skipped(self):
        runner = FakeRunner(
            [
                (
                    ("dpkg-query", "-W"),
                    FakeResult(0, "libbrotli1\t1.2.0-3build1\n", "dpkg-query: no path"),
                )
            ]
        )
        packages = find_system_packages(runner, ["libbrotli1", "brotli"])
        self.assertEqual([p.name for p in packages], ["libbrotli1"])

    def test_rpm_fallback_when_dpkg_absent(self):
        runner = FakeRunner(
            [
                (("dpkg-query",), FakeResult(127, "", "not found")),
                (("rpm", "-q"), FakeResult(0, "libbrotli1-1.2.0-3.fc42.x86_64\n", "")),
            ]
        )
        packages = find_system_packages(runner, ["libbrotli1"])
        self.assertEqual(packages[0].manager, "rpm")
        self.assertTrue(packages[0].version.startswith("1.2.0"))

    def test_no_package_manager_yields_empty(self):
        runner = FakeRunner([(("dpkg-query",), FakeResult(127, "", "")),
                             (("rpm",), FakeResult(127, "", ""))])
        self.assertEqual(find_system_packages(runner, ["libbrotli1"]), [])

    def test_debian_line_parser_rejects_blank(self):
        self.assertIsNone(parse_debian_version_line("   "))


if __name__ == "__main__":
    unittest.main()
