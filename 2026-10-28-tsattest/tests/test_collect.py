"""Probe collection: which surface each fact comes from, and what happens when one cannot be read."""

import os
import unittest

import helpers
from tsattest import collect


SERVE_HTTP_ONLY = (
    "https://jarmes.taildfb99c.ts.net (tailnet only)\n"
    "|-- / proxy http://127.0.0.1:3000\n"
)

SERVE_WITH_UNIX = (
    "https://jarmes.taildfb99c.ts.net (tailnet only)\n"
    "|-- /docker unix:/var/run/docker.sock\n"
)


class TestVersionSurface(unittest.TestCase):
    def test_reads_first_line_of_tailscale_version(self):
        root = helpers.write_fixtures(helpers.tempdir(), version="1.102.3",
                                      prefs=helpers.PREFS_SSH_ON)
        c = collect.gather(fixtures=root)
        self.assertEqual((c.facts.version.major, c.facts.version.minor,
                          c.facts.version.patch), (1, 102, 3))

    def test_missing_version_probe_is_unmeasurable_not_unknown_version(self):
        root = helpers.write_fixtures(helpers.tempdir(), version=None,
                                      prefs=helpers.PREFS_SSH_ON)
        c = collect.gather(fixtures=root)
        self.assertIsNone(c.facts.version)
        probe = c.probe("version")
        self.assertEqual(probe.status, collect.UNREADABLE)
        self.assertTrue(probe.reason)

    def test_unparseable_version_line_is_unmeasurable(self):
        root = helpers.write_fixtures(helpers.tempdir(), prefs=helpers.PREFS_SSH_ON)
        with open(os.path.join(root, "version.txt"), "w") as fh:
            fh.write("not a version at all\n")
        c = collect.gather(fixtures=root)
        self.assertIsNone(c.facts.version)
        self.assertIn("1.102.3", c.probe("version").reason)


class TestSshSurface(unittest.TestCase):
    def test_ssh_state_comes_from_prefs_not_status(self):
        # The whole point: SSH_HostKeys null but RunSSH true on the same host.
        status = helpers.status_doc(ssh_host_keys=None)
        root = helpers.write_fixtures(helpers.tempdir(), prefs=helpers.PREFS_SSH_ON,
                                      status=status)
        c = collect.gather(fixtures=root)
        self.assertIs(c.facts.ssh_enabled, True)
        self.assertEqual(c.ssh_source, "tailscale debug prefs")

    def test_status_surface_contradiction_is_recorded_not_used(self):
        status = helpers.status_doc(ssh_host_keys=None)
        root = helpers.write_fixtures(helpers.tempdir(), prefs=helpers.PREFS_SSH_ON,
                                      status=status)
        c = collect.gather(fixtures=root)
        self.assertIs(c.ssh_host_keys_present, False)
        self.assertTrue(any("SSH_HostKeys" in n for n in c.notes))

    def test_prefs_ssh_off(self):
        root = helpers.write_fixtures(helpers.tempdir(), prefs=helpers.PREFS_SSH_OFF,
                                      status=helpers.status_doc())
        c = collect.gather(fixtures=root)
        self.assertIs(c.facts.ssh_enabled, False)

    def test_broken_prefs_json_is_unmeasurable(self):
        root = helpers.write_fixtures(helpers.tempdir(), prefs="{not json")
        c = collect.gather(fixtures=root)
        self.assertIsNone(c.facts.ssh_enabled)
        self.assertEqual(c.probe("prefs").status, collect.UNREADABLE)


class TestServeSurface(unittest.TestCase):
    def test_http_only_backend_is_not_a_unix_backend(self):
        root = helpers.write_fixtures(helpers.tempdir(), prefs=helpers.PREFS_SSH_ON,
                                      serve=SERVE_HTTP_ONLY)
        c = collect.gather(fixtures=root)
        self.assertIs(c.facts.serve_present, True)
        self.assertIs(c.facts.serve_unix_backend, False)

    def test_unix_backend_detected(self):
        root = helpers.write_fixtures(helpers.tempdir(), prefs=helpers.PREFS_SSH_ON,
                                      serve=SERVE_WITH_UNIX)
        c = collect.gather(fixtures=root)
        self.assertIs(c.facts.serve_unix_backend, True)

    def test_empty_serve_output_means_no_serve_config(self):
        root = helpers.write_fixtures(helpers.tempdir(), prefs=helpers.PREFS_SSH_ON,
                                      serve="")
        c = collect.gather(fixtures=root)
        self.assertIs(c.facts.serve_present, False)

    def test_missing_serve_probe_is_unmeasurable(self):
        root = helpers.write_fixtures(helpers.tempdir(), prefs=helpers.PREFS_SSH_ON,
                                      serve=None)
        c = collect.gather(fixtures=root)
        self.assertIsNone(c.facts.serve_present)
        self.assertEqual(c.probe("serve").status, collect.UNREADABLE)


SERVE_TWO_MOUNTS = (
    "https://jarmes.taildfb99c.ts.net (tailnet only)\n"
    "|-- / proxy http://127.0.0.1:3000\n"
    "|-- /api proxy http://127.0.0.1:8080\n"
)


class TestServeShape(unittest.TestCase):
    def test_mount_count_is_parsed(self):
        root = helpers.write_fixtures(helpers.tempdir(), prefs=helpers.PREFS_SSH_ON,
                                      serve=SERVE_TWO_MOUNTS)
        c = collect.gather(fixtures=root)
        self.assertEqual(c.facts.serve_mounts, 2)

    def test_single_mount_is_counted_as_one(self):
        root = helpers.write_fixtures(helpers.tempdir(), prefs=helpers.PREFS_SSH_ON,
                                      serve=SERVE_HTTP_ONLY)
        c = collect.gather(fixtures=root)
        self.assertEqual(c.facts.serve_mounts, 1)

    def test_https_mount_means_tls(self):
        root = helpers.write_fixtures(helpers.tempdir(), prefs=helpers.PREFS_SSH_ON,
                                      serve=SERVE_HTTP_ONLY)
        self.assertIs(collect.gather(fixtures=root).facts.serve_tls, True)

    def test_plain_http_serve_is_not_tls(self):
        root = helpers.write_fixtures(helpers.tempdir(), prefs=helpers.PREFS_SSH_ON,
                                      serve="http://jarmes:8080 (tailnet only)\n"
                                            "|-- / proxy http://127.0.0.1:3000\n")
        self.assertIs(collect.gather(fixtures=root).facts.serve_tls, False)


class TestMitigationThreeWaySplit(unittest.TestCase):
    """declared (config file) vs actual (running process) vs unmeasurable."""

    def test_declared_one_actual_unreadable_is_unknown_never_mitigated(self):
        declared = 'FLAGS=""\nTS_SSH_DISABLE_FORWARDING="1"\n'
        root = helpers.write_fixtures(helpers.tempdir(), prefs=helpers.PREFS_SSH_ON,
                                      defaults=declared, environ=None)
        c = collect.gather(fixtures=root)
        self.assertEqual(c.mitigation.declared.value, "1")
        self.assertEqual(c.mitigation.actual.status, collect.UNREADABLE)
        self.assertEqual(c.mitigation.consistency, collect.UNKNOWN)
        self.assertNotEqual(c.mitigation.consistency, collect.CONSISTENT)

    def test_declared_and_actual_agree(self):
        declared = 'TS_SSH_DISABLE_FORWARDING="1"\n'
        environ = "PATH=/usr/sbin\x00TS_SSH_DISABLE_FORWARDING=1\x00HOME=/root\x00"
        root = helpers.write_fixtures(helpers.tempdir(), prefs=helpers.PREFS_SSH_ON,
                                      defaults=declared, environ=environ)
        c = collect.gather(fixtures=root)
        self.assertEqual(c.mitigation.actual.value, "1")
        self.assertEqual(c.mitigation.consistency, collect.CONSISTENT)

    def test_declared_one_but_process_lacks_it_is_a_disagreement(self):
        declared = 'TS_SSH_DISABLE_FORWARDING="1"\n'
        environ = "PATH=/usr/sbin\x00HOME=/root\x00"
        root = helpers.write_fixtures(helpers.tempdir(), prefs=helpers.PREFS_SSH_ON,
                                      defaults=declared, environ=environ)
        c = collect.gather(fixtures=root)
        self.assertEqual(c.mitigation.actual.value, "")
        self.assertEqual(c.mitigation.consistency, collect.DISAGREE)

    def test_undeclared_and_absent_in_process_is_both_unset(self):
        environ = "PATH=/usr/sbin\x00HOME=/root\x00"
        root = helpers.write_fixtures(helpers.tempdir(), prefs=helpers.PREFS_SSH_ON,
                                      defaults="# no vars here\nPORT=\"41641\"\n",
                                      environ=environ)
        c = collect.gather(fixtures=root)
        self.assertEqual(c.mitigation.consistency, collect.CONSISTENT)
        self.assertEqual(c.mitigation.actual.value, "")


class TestProbeAccounting(unittest.TestCase):
    def test_every_probe_is_counted(self):
        root = helpers.write_fixtures(helpers.tempdir(), prefs=helpers.PREFS_SSH_ON,
                                      status=helpers.status_doc(), serve=SERVE_HTTP_ONLY)
        c = collect.gather(fixtures=root)
        self.assertEqual(c.probe_count(), 6)
        self.assertEqual(c.measured_count() + c.unmeasurable_count(), c.probe_count())
        self.assertEqual(c.unmeasurable_count(), 2)  # environ + defaults absent

    def test_probe_names_are_stable(self):
        root = helpers.write_fixtures(helpers.tempdir(), prefs=helpers.PREFS_SSH_ON)
        c = collect.gather(fixtures=root)
        self.assertEqual([p.name for p in c.probes],
                         ["version", "prefs", "status", "serve", "env", "defaults"])

    def test_real_proc_environ_shape_is_nul_separated(self):
        self.assertEqual(collect.parse_environ("A=1\x00B=2\x00"), {"A": "1", "B": "2"})
        self.assertEqual(collect.parse_environ(""), {})
        self.assertEqual(collect.parse_environ("MALFORMED\x00A=1\x00"), {"A": "1"})


if __name__ == "__main__":
    unittest.main()
