"""The real corpus, not my fixtures.

These three payloads were recorded live on 2026-10-31 from the real endpoints
(850 / 175 / 356 components). Self-authored fixtures only prove I am consistent with
myself; this file proves the selector rules survive a real payload's shape.
"""
import json
import os
import unittest

from exitpath.models import Fetch
from exitpath.statuspage import select_exit
from exitpath.venues import VENUES, evaluate_venue

REAL = os.path.join(os.path.dirname(__file__), "fixtures", "real")

FILES = {
    "kraken": "kraken-components.json",
    "coinbase": "coinbase-components.json",
    "usdc": "circle-components.json",
}


def load(slug):
    with open(os.path.join(REAL, FILES[slug]), "rb") as fh:
        return fh.read()


class RealCorpusTests(unittest.TestCase):
    def setUp(self):
        self.venues = {v.slug: v for v in VENUES}

    def test_every_statuspage_venue_selects_something_in_the_real_payload(self):
        for slug in FILES:
            with self.subTest(venue=slug):
                venue = self.venues[slug]
                exit_ = evaluate_venue(venue, Fetch(200, load(slug), None))
                self.assertTrue(exit_.measurable, exit_.reason)
                self.assertGreater(len(exit_.signals), 0)

    def test_real_payloads_still_parse_and_keep_observed_at(self):
        for slug in FILES:
            with self.subTest(venue=slug):
                exit_ = evaluate_venue(self.venues[slug], Fetch(200, load(slug), None))
                self.assertTrue(exit_.observed_at, "statuspage always publishes updated_at")

    def test_usdc_redeeming_rows_are_found_per_chain(self):
        from exitpath.statuspage import parse_page
        page = parse_page(json.loads(load("usdc")))
        selected = select_exit(page.components, self.venues["usdc"].selectors)
        redeeming = [c.name for c in selected if c.name.endswith("- Redeeming")]
        self.assertGreaterEqual(len(redeeming), 5, redeeming)
        self.assertTrue(all(n.startswith(("USDC - ", "EURC - ")) for n in redeeming), redeeming)
        self.assertTrue(any(n.startswith("USDC - ") for n in redeeming))

    def test_kraken_parent_group_is_carried_as_a_signal(self):
        exit_ = evaluate_venue(self.venues["kraken"], Fetch(200, load("kraken"), None))
        self.assertTrue(any(s.note == "parent group state" for s in exit_.signals))

    def test_selection_is_a_small_slice_of_a_huge_page(self):
        payload = json.loads(load("kraken"))
        from exitpath.statuspage import parse_page
        page = parse_page(payload)
        selected = select_exit(page.components, self.venues["kraken"].selectors)
        # Kraken's funding group is 733 per-asset rows -- the selection is legitimately large,
        # so what must stay small is the *reported* signal list, not the checked count.
        self.assertGreater(len(selected), 300)
        exit_ = evaluate_venue(self.venues["kraken"], Fetch(200, load("kraken"), None))
        self.assertEqual(exit_.checked, len(selected))
        self.assertLess(len(exit_.signals), 40, "only non-open components may be reported")

    def test_open_components_are_counted_not_listed(self):
        exit_ = evaluate_venue(self.venues["coinbase"], Fetch(200, load("coinbase"), None))
        open_signals = [s for s in exit_.signals if s.state == "open" and s.note != "parent group state"]
        self.assertEqual(open_signals, [])


if __name__ == "__main__":
    unittest.main()
