"""RED-first tests for venue exit evaluation."""
import json
import unittest

from exitpath.models import Fetch, HALTED, OPEN, DEGRADED, UNMEASURABLE
from exitpath.statuspage import Selector
from exitpath.venues import Venue, evaluate_venue, VENUES


def doc(comps):
    return json.dumps({"page": {"name": "T"}, "components": comps}).encode()


KRAKEN_KIND = Venue(
    slug="kraken",
    name="Kraken",
    kind="statuspage",
    components_url="https://status.kraken.com/api/v2/components.json",
    selectors=Selector(groups=("Digital Currency Funding",), patterns=(r"Wire Transfer",)),
    network_rule="kraken_suffix",
    note="",
)

TIMESTAMP = "2026-10-31T05:04:17.955Z"


class VenueTests(unittest.TestCase):
    def test_all_operational_is_open(self):
        body = doc([
            {"id": "g1", "name": "Digital Currency Funding", "status": "operational", "group": True, "group_id": None},
            {"id": "c1", "name": "USDC (USDC) - Base", "status": "operational", "group": False, "group_id": "g1"},
        ])
        exit_ = evaluate_venue(KRAKEN_KIND, Fetch(200, body, None))
        self.assertEqual(exit_.state, OPEN)
        self.assertTrue(exit_.measurable)
        self.assertEqual(exit_.paused_networks, ())

    def test_partial_outage_component_is_halted_and_names_the_network(self):
        body = doc([
            {"id": "g1", "name": "Digital Currency Funding", "status": "operational", "group": True, "group_id": None},
            {"id": "c1", "name": "USDC (USDC) - Solana", "status": "partial_outage", "group": False, "group_id": "g1"},
            {"id": "c2", "name": "USDC (USDC) - Base", "status": "operational", "group": False, "group_id": "g1"},
        ])
        exit_ = evaluate_venue(KRAKEN_KIND, Fetch(200, body, None))
        self.assertEqual(exit_.state, HALTED)
        self.assertEqual(exit_.paused_networks, ("Solana",))

    def test_degraded_parent_group_alone_counts(self):
        # Real Kraken condition on 2026-10-31: parent degraded, every child operational.
        body = doc([
            {"id": "g1", "name": "Digital Currency Funding", "status": "degraded_performance",
             "group": True, "group_id": None},
            {"id": "c1", "name": "USDC (USDC) - Base", "status": "operational", "group": False, "group_id": "g1"},
        ])
        exit_ = evaluate_venue(KRAKEN_KIND, Fetch(200, body, None))
        self.assertEqual(exit_.state, DEGRADED)
        self.assertEqual(exit_.degraded_networks, ())

    def test_http_404_is_unmeasurable_never_operational(self):
        exit_ = evaluate_venue(KRAKEN_KIND, Fetch(404, b"not found", None))
        self.assertEqual(exit_.state, UNMEASURABLE)
        self.assertFalse(exit_.measurable)
        self.assertIn("404", exit_.reason)

    def test_transport_error_is_unmeasurable(self):
        exit_ = evaluate_venue(KRAKEN_KIND, Fetch(0, b"", "timed out"))
        self.assertEqual(exit_.state, UNMEASURABLE)
        self.assertIn("timed out", exit_.reason)

    def test_valid_json_with_no_matching_component_is_unmeasurable(self):
        body = doc([{"id": "c9", "name": "Blog", "status": "operational", "group": False, "group_id": None}])
        exit_ = evaluate_venue(KRAKEN_KIND, Fetch(200, body, None))
        self.assertEqual(exit_.state, UNMEASURABLE)
        self.assertIn("no exit-relevant", exit_.reason)

    def test_unparseable_body_is_unmeasurable(self):
        exit_ = evaluate_venue(KRAKEN_KIND, Fetch(200, b"<html>", None))
        self.assertEqual(exit_.state, UNMEASURABLE)

    def test_venue_page_indicator_is_surfaced_even_when_slice_is_open(self):
        body = doc([
            {"id": "g1", "name": "Digital Currency Funding", "status": "operational",
             "group": True, "group_id": None},
            {"id": "c1", "name": "USDC (USDC) - Base", "status": "operational",
             "group": False, "group_id": "g1"},
        ])
        indicator = Fetch(200, json.dumps({"status": {"indicator": "minor",
                                                      "description": "Partially Degraded Service"}}).encode(), None)
        exit_ = evaluate_venue(KRAKEN_KIND, Fetch(200, body, None), indicator)
        self.assertEqual(exit_.state, OPEN)
        self.assertIn("minor", exit_.page_status)

    def test_broken_indicator_fetch_does_not_change_state(self):
        body = doc([
            {"id": "g1", "name": "Digital Currency Funding", "status": "operational",
             "group": True, "group_id": None},
            {"id": "c1", "name": "USDC (USDC) - Base", "status": "operational", "group": False, "group_id": "g1"},
        ])
        exit_ = evaluate_venue(KRAKEN_KIND, Fetch(200, body, None), Fetch(0, b"", "timed out"))
        self.assertEqual(exit_.state, OPEN)
        self.assertIsNone(exit_.page_status)

    def test_venue_none_indicator_is_not_surfaced(self):
        body = doc([
            {"id": "c1", "name": "USDC (USDC) - Base", "status": "operational", "group": False, "group_id": "g1"},
            {"id": "g1", "name": "Digital Currency Funding", "status": "operational", "group": True, "group_id": None},
        ])
        indicator = Fetch(200, b'{"status":{"indicator":"none"}}', None)
        self.assertIsNone(evaluate_venue(KRAKEN_KIND, Fetch(200, body, None), indicator).page_status)

    def test_status_url_is_derived_only_for_statuspage_venues(self):
        self.assertEqual(KRAKEN_KIND.status_url,
                         "https://status.kraken.com/api/v2/status.json")
        binance = [v for v in VENUES if v.slug == "binance"][0]
        self.assertIsNone(binance.status_url)

    def test_network_lists_are_deduplicated(self):
        body = doc([
            {"id": "g1", "name": "Digital Currency Funding", "status": "operational", "group": True, "group_id": None},
            {"id": "c1", "name": "USDC (USDC) - Solana", "status": "partial_outage", "group": False, "group_id": "g1"},
            {"id": "c2", "name": "Some Token (TOK) - Solana", "status": "major_outage", "group": False, "group_id": "g1"},
        ])
        exit_ = evaluate_venue(KRAKEN_KIND, Fetch(200, body, None))
        self.assertEqual(exit_.paused_networks, ("Solana",))

    def test_observed_at_comes_from_the_page_not_the_clock(self):
        body = json.dumps({"page": {"updated_at": TIMESTAMP}, "components": [
            {"id": "c1", "name": "USDC (USDC) - Base", "status": "operational", "group": False,
             "group_id": "g1"},
            {"id": "g1", "name": "Digital Currency Funding", "status": "operational",
             "group": True, "group_id": None},
        ]}).encode()
        exit_ = evaluate_venue(KRAKEN_KIND, Fetch(200, body, None))
        self.assertEqual(exit_.observed_at, TIMESTAMP)


class RegistryTests(unittest.TestCase):
    def test_registry_has_unique_slugs(self):
        slugs = [v.slug for v in VENUES]
        self.assertEqual(len(slugs), len(set(slugs)))

    def test_uncovered_venue_declares_a_probe_url_and_no_components_url(self):
        binance = [v for v in VENUES if v.slug == "binance"][0]
        self.assertEqual(binance.kind, "uncovered")
        self.assertIsNone(binance.components_url)
        self.assertTrue(binance.probe_url)


if __name__ == "__main__":
    unittest.main()
