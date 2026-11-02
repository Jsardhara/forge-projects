"""Parsing the Ubuntu CVE page. Fixtures: one genuine excerpt trimmed from today's real
page (tests/fixtures/ubuntu_cve_excerpt.html) plus inline snippets for status variants that
today's page does not happen to contain but tomorrow's will."""

import os
import unittest

from cvewatch.tracker import CvePage, Row, parse, pick_row, rows_for_release

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "ubuntu_cve_excerpt.html")


def _page(rows_html, title="CVE-2026-98432 | Ubuntu"):
    return (
        "<!doctype html><html><head><title>%s</title></head><body>"
        '<table class="cve-table"><thead><tr><th>Package</th><th>Ubuntu Release</th>'
        "<th>Status</th></tr></thead><tbody>%s</tbody></table></body></html>"
        % (title, rows_html)
    )


def _row(package, rowspan, release, status):
    return (
        '<tr><th rowspan="%d">%s</th><td>%s</td>'
        '<td class="cve-td-status"><div>%s</div></td></tr>'
        % (rowspan, package, release, status)
    )


class RealExcerptTests(unittest.TestCase):
    """The parser against markup as Ubuntu actually served it on 2026-11-02."""

    @classmethod
    def setUpClass(cls):
        with open(FIXTURE, encoding="utf-8") as handle:
            cls.page = parse(handle.read())

    def test_cve_id_from_title(self):
        self.assertEqual(self.page.cve_id, "CVE-2026-98432")

    def test_row_count(self):
        self.assertEqual(len(self.page.rows), 12)

    def test_package_rowspan_carries_down(self):
        packages = {row.package for row in self.page.rows}
        self.assertEqual(packages, {"linux", "linux-hwe"})

    def test_lts_release_id_and_codename(self):
        row = pick_row(self.page, "linux", "26.04")
        self.assertIsNotNone(row)
        self.assertEqual(row.release_id, "26.04")
        self.assertEqual(row.codename, "resolute")

    def test_non_lts_release(self):
        row = pick_row(self.page, "linux", "26.10")
        self.assertEqual(row.codename, "stonking")

    def test_work_in_progress_target(self):
        row = pick_row(self.page, "linux", "26.04")
        self.assertEqual(row.kind, "vulnerable")
        self.assertEqual(row.fixed_version, "7.0.0-43.43")
        self.assertFalse(row.released)

    def test_not_affected_is_patched(self):
        row = pick_row(self.page, "linux", "14.04")
        self.assertEqual(row.kind, "patched")

    def test_not_in_release(self):
        row = pick_row(self.page, "linux-hwe", "26.04")
        self.assertEqual(row.kind, "not_in_release")

    def test_all_rows_have_a_known_kind(self):
        kinds = {row.kind for row in self.page.rows}
        self.assertTrue(kinds <= {"vulnerable", "patched", "not_in_release", "ignored",
                                 "pending", "unknown"}, kinds)


class StatusVariantTests(unittest.TestCase):
    def test_plain_vulnerable_has_no_target(self):
        page = parse(_page(_row("linux", 2, "26.04 LTS resolute", "Vulnerable")))
        row = page.rows[0]
        self.assertEqual(row.kind, "vulnerable")
        self.assertEqual(row.fixed_version, "")
        self.assertFalse(row.released)

    def test_fix_released_wording(self):
        page = parse(_page(_row("linux", 2, "26.04 LTS resolute",
                                "Vulnerable, fix released in 7.0.0-43.43")))
        row = page.rows[0]
        self.assertEqual(row.kind, "vulnerable")
        self.assertEqual(row.fixed_version, "7.0.0-43.43")
        self.assertTrue(row.released)

    def test_ignored_keeps_reason(self):
        page = parse(_page(_row("linux", 2, "20.04 LTS focal",
                                "Ignored end of standard support")))
        row = page.rows[0]
        self.assertEqual(row.kind, "ignored")
        self.assertIn("end of standard support", row.detail)

    def test_pending_status(self):
        page = parse(_page(_row("linux", 2, "26.04 LTS resolute", "Pending")))
        self.assertEqual(page.rows[0].kind, "pending")

    def test_unknown_status_is_kept_not_dropped(self):
        page = parse(_page(_row("linux", 2, "26.04 LTS resolute", "Needed")))
        self.assertEqual(page.rows[0].kind, "unknown")
        self.assertEqual(page.rows[0].detail, "Needed")

    def test_no_table_is_an_empty_page_not_a_crash(self):
        page = parse("<html><head><title>CVE-2026-0001 | Ubuntu</title></head><body></body></html>")
        self.assertEqual(page.cve_id, "CVE-2026-0001")
        self.assertEqual(page.rows, ())

    def test_blank_input(self):
        page = parse("")
        self.assertEqual(page.cve_id, "")
        self.assertEqual(page.rows, ())

    def test_fips_variant_is_not_plain(self):
        page = parse(_page(
            _row("linux", 4, "24.04 LTS noble", "Vulnerable work in progress in 6.8.0-149.149")
            + _row("linux", 4, "24.04 LTS noble FIPS Updates FIPS-140 certified package with "
                               "security fixes. Available with Ubuntu Pro.",
                   "Not affected")))
        plain = pick_row(page, "linux", "24.04")
        self.assertEqual(plain.kind, "vulnerable")
        self.assertEqual(plain.qualifier, "")


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.page = CvePage(
            cve_id="CVE-2026-98432",
            source="test",
            rows=(
                Row("linux", "26.04 LTS resolute", "26.04", "resolute", "", "vulnerable",
                    "7.0.0-43.43", False, "Vulnerable work in progress in 7.0.0-43.43"),
                Row("linux", "26.10 stonking", "26.10", "stonking", "", "vulnerable",
                    "7.3.0-10.10", False, "Vulnerable work in progress in 7.3.0-10.10"),
                Row("linux-hwe", "26.04 LTS resolute", "26.04", "resolute", "",
                    "not_in_release", "", False, "Not in release"),
            ),
        )

    def test_rows_for_release(self):
        self.assertEqual(len(rows_for_release(self.page, "26.04")), 2)

    def test_pick_row_by_package_and_release(self):
        row = pick_row(self.page, "linux", "26.04")
        self.assertEqual(row.fixed_version, "7.0.0-43.43")

    def test_pick_row_missing_returns_none(self):
        self.assertIsNone(pick_row(self.page, "linux", "24.04"))

    def test_pick_row_matches_codename_too(self):
        row = pick_row(self.page, "linux", "", "stonking")
        self.assertEqual(row.release_id, "26.10")


if __name__ == "__main__":
    unittest.main()
