"""RED-first tests for the report: exit contract, JSON shape, honest coverage."""
import json
import unittest

from exitpath.chains import ChainHealth
from exitpath.models import VenueExit, HALTED, OPEN, DEGRADED, UNMEASURABLE, Signal
from exitpath.report import build_report, render_text, verdict


def venue(slug, state, paused=(), reason=None, kind="venue"):
    return VenueExit(slug=slug, name=slug.title(), kind=kind, state=state, signals=(),
                     paused_networks=tuple(paused), degraded_networks=(),
                     source_url="https://example.invalid", http_code=200 if state != UNMEASURABLE else 404,
                     confidence=1.0 if state != UNMEASURABLE else 0.0, reason=reason)


def chain(slug, ok):
    return ChainHealth(chain=slug, endpoint="https://example.invalid", ok=ok,
                       block_height=16 if ok else None, latency_ms=1.0,
                       error=None if ok else "Cannot fulfill request")


class VerdictTests(unittest.TestCase):
    def test_all_open_is_clean(self):
        self.assertEqual(verdict((venue("a", OPEN),), (chain("ethereum", True),)), 0)

    def test_halted_is_a_finding(self):
        self.assertEqual(verdict((venue("a", HALTED),), (chain("ethereum", True),)), 1)

    def test_degraded_is_a_finding(self):
        self.assertEqual(verdict((venue("a", DEGRADED),), (chain("ethereum", True),)), 1)

    def test_dead_chain_is_a_finding(self):
        self.assertEqual(verdict((venue("a", OPEN),), (chain("ethereum", False),)), 1)

    def test_unmeasurable_alone_is_exit_2(self):
        self.assertEqual(verdict((venue("a", UNMEASURABLE, reason="404"),), (chain("ethereum", True),)), 2)

    def test_declared_uncovered_venue_does_not_force_exit_2(self):
        v = (venue("a", OPEN), venue("binance", UNMEASURABLE, reason="404", kind="uncovered"))
        self.assertEqual(verdict(v, (chain("ethereum", True),)), 0)

    def test_finding_outranks_unmeasurable(self):
        v = (venue("a", UNMEASURABLE, reason="404"), venue("b", HALTED))
        self.assertEqual(verdict(v, (chain("ethereum", True),)), 1)


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.venues = (venue("kraken", DEGRADED), venue("binance", UNMEASURABLE, reason="no public status JSON (HTTP 404)"))
        self.chains = (chain("ethereum", True), chain("solana", False))
        self.report = build_report(self.venues, self.chains, now="2026-10-31T06:40:00Z")

    def test_json_round_trips(self):
        parsed = json.loads(json.dumps(self.report))
        self.assertEqual(parsed["now"], "2026-10-31T06:40:00Z")
        self.assertEqual(parsed["exit_code"], 1)

    def test_coverage_is_explicit(self):
        cov = self.report["coverage"]
        self.assertEqual(cov["venues_total"], 2)
        self.assertEqual(cov["venues_measured"], 1)
        self.assertEqual(cov["chains_total"], 2)
        self.assertEqual(cov["chains_healthy"], 1)

    def test_text_names_the_unmeasurable_venue_and_why(self):
        text = render_text(self.report)
        self.assertIn("binance", text)
        self.assertIn("unmeasurable", text.lower())
        self.assertIn("404", text)

    def test_text_names_the_halted_component(self):
        v = VenueExit(
            slug="usdc", name="Circle", kind="statuspage", state=HALTED,
            signals=(Signal("Circle Cross-Chain Transfer Protocol (group)", HALTED, "parent group state"),),
            source_url="https://example.invalid", http_code=200, confidence=1.0, checked=87,
        )
        text = render_text(build_report((v,), (chain("ethereum", True),), now="t"))
        self.assertIn("Circle Cross-Chain Transfer Protocol", text)
        self.assertNotIn("all open", text)

    def test_text_never_prints_a_secret_shaped_value(self):
        text = render_text(self.report)
        for bad in ("sk-", "AKIA", "Bearer "):
            self.assertNotIn(bad, text)

    def test_text_shows_exit_code_line(self):
        self.assertIn("exit", render_text(self.report).lower())


if __name__ == "__main__":
    unittest.main()
