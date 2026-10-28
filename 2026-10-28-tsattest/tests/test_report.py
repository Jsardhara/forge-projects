"""Report building and rendering: the verdict contract and what each output must state."""

import json
import unittest

import helpers
from tsattest import collect, report


def gathered(version="1.102.3", prefs=helpers.PREFS_SSH_ON, status=None,
             serve="https://x.ts.net (tailnet only)\n|-- / proxy http://127.0.0.1:3000\n",
             defaults="PORT=\"41641\"\n", environ="PATH=/usr/sbin\x00HOME=/root\x00"):
    if status is None:
        status = helpers.status_doc(ssh_host_keys=None)
    root = helpers.write_fixtures(helpers.tempdir(), version=version, prefs=prefs,
                                  status=status, serve=serve, defaults=defaults,
                                  environ=environ)
    return collect.gather(fixtures=root)


class TestVerdictContract(unittest.TestCase):
    def test_vulnerable_host_fails_with_exit_one(self):
        r = report.build_report(gathered())
        self.assertEqual(r["verdict"], "FAIL")
        self.assertEqual(r["exit_code"], 1)

    def test_patched_host_passes_with_exit_zero(self):
        r = report.build_report(gathered(version="1.104.4"))
        self.assertEqual(r["verdict"], "PASS")
        self.assertEqual(r["exit_code"], 0)

    def test_unmeasurable_version_cannot_pass(self):
        r = report.build_report(gathered(version=None))
        self.assertEqual(r["verdict"], "UNKNOWN")
        self.assertEqual(r["exit_code"], 2)

    def test_unmeasurable_serve_cannot_pass(self):
        r = report.build_report(gathered(version="1.104.4", serve=None))
        self.assertEqual(r["verdict"], "UNKNOWN")
        self.assertEqual(r["exit_code"], 2)

    def test_a_pass_requires_the_runtime_value_and_says_so(self):
        r = report.build_report(gathered(version="1.104.4"))
        self.assertIn("debug prefs", r["ssh"]["source"])
        self.assertNotIn("SSH_HostKeys", r["ssh"]["source"])


class TestNeverInferFromConfigFile(unittest.TestCase):
    def test_declared_mitigation_never_upgrades_an_unknown_verdict(self):
        # serve unreadable => UNKNOWN verdict. A mitigation declared in the
        # EnvironmentFile must not be allowed to turn that into a PASS.
        r = report.build_report(gathered(
            version="1.104.4",
            defaults='TS_SSH_DISABLE_FORWARDING="1"\n',
            environ=None,
            serve=None))
        self.assertEqual(r["verdict"], "UNKNOWN")
        self.assertEqual(r["mitigation"]["consistency"], "UNKNOWN")
        text = report.render_plain(r)
        self.assertIn("UNKNOWN", text)
        self.assertIn("needs root", text)

    def test_mitigation_is_reported_even_when_the_verdict_is_decided_by_version(self):
        r = report.build_report(gathered(defaults='TS_SSH_DISABLE_FORWARDING="1"\n',
                                         environ=None))
        self.assertEqual(r["mitigation"]["declared"]["value"], "1")
        self.assertEqual(r["mitigation"]["actual"]["status"], "unreadable")

    def test_reason_names_the_fact_and_the_flag(self):
        r = report.build_report(gathered(defaults='TS_SSH_DISABLE_FORWARDING="1"\n',
                                         environ=None))
        advice = r["mitigation"]["advice"]
        self.assertIn("TS_SSH_DISABLE_FORWARDING", advice)
        self.assertIn("root", advice)

    def test_disagreement_between_file_and_process_is_stated(self):
        r = report.build_report(gathered(defaults='TS_SSH_DISABLE_FORWARDING="1"\n',
                                         environ="PATH=/usr/sbin\x00HOME=/root\x00"))
        self.assertEqual(r["mitigation"]["consistency"], "DISAGREE")
        self.assertIn("DISAGREE", report.render_plain(r))


class TestRendering(unittest.TestCase):
    def test_plain_output_lists_every_bulletin(self):
        text = report.render_plain(report.build_report(gathered()))
        for key in ("TS-2026-013", "TS-2026-014", "TS-2026-015",
                    "TS-2026-016", "TS-2026-017"):
            self.assertIn(key, text)

    def test_plain_output_reports_probe_accounting(self):
        text = report.render_plain(report.build_report(gathered()))
        self.assertIn("probed", text)
        self.assertIn("measured", text)

    def test_plain_output_shows_status_counts_for_the_bulletin_branch(self):
        text = report.render_plain(report.build_report(gathered()))
        self.assertIn("open", text)
        self.assertIn("not applicable", text)

    def test_json_is_parseable_and_carries_the_same_verdict(self):
        r = report.build_report(gathered())
        doc = json.loads(report.render_json(r))
        self.assertEqual(doc["verdict"], "FAIL")
        self.assertEqual(doc["exit_code"], 1)
        self.assertEqual(len(doc["bulletins"]), 5)

    def test_contradiction_note_is_rendered(self):
        text = report.render_plain(report.build_report(gathered()))
        self.assertIn("SSH_HostKeys", text)


class TestNegativeControls(unittest.TestCase):
    def test_clean_input_says_clean(self):
        r = report.build_report(gathered(version="1.104.4"))
        self.assertIn("PASS", r["verdict"])

    def test_empty_input_is_not_a_pass(self):
        root = helpers.write_fixtures(helpers.tempdir(), version=None)
        r = report.build_report(collect.gather(fixtures=root))
        self.assertEqual(r["verdict"], "UNKNOWN")
        self.assertIn("0 of 6", report.render_plain(r))

    def test_unreadable_input_names_the_path(self):
        root = helpers.write_fixtures(helpers.tempdir(), version=None)
        c = collect.gather(fixtures=root)
        reasons = " ".join(p.reason or "" for p in c.probes)
        self.assertIn("version.txt", reasons)


if __name__ == "__main__":
    unittest.main()
