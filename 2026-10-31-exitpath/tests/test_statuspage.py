"""RED-first tests for statuspage parsing and exit-component selection."""
import unittest

from exitpath.statuspage import parse_components, select_exit, network_from_name, Selector


KRAKEN = {
    "page": {"name": "Kraken"},
    "components": [
        {"id": "g1", "name": "Digital Currency Funding", "status": "degraded_performance",
         "group": True, "group_id": None},
        {"id": "g2", "name": "Payment Methods", "status": "operational", "group": True, "group_id": None},
        {"id": "c1", "name": "USDC (USDC) - Base", "status": "operational", "group": False, "group_id": "g1"},
        {"id": "c2", "name": "USDC (USDC) - Solana", "status": "partial_outage", "group": False, "group_id": "g1"},
        {"id": "c3", "name": "Euro (EUR) - Wire Transfer Deposits", "status": "major_outage",
         "group": False, "group_id": "g2"},
        {"id": "c4", "name": "Website", "status": "operational", "group": False, "group_id": None},
    ],
}


class ParseTests(unittest.TestCase):
    def test_parent_resolved_from_group_id(self):
        comps = {c.name: c for c in parse_components(KRAKEN)}
        self.assertEqual(comps["USDC (USDC) - Base"].parent, "Digital Currency Funding")
        self.assertIsNone(comps["Website"].parent)

    def test_group_flag_survives(self):
        comps = {c.name: c for c in parse_components(KRAKEN)}
        self.assertTrue(comps["Digital Currency Funding"].is_group)

    def test_tolerates_boolean_group_field_and_missing_page(self):
        payload = {"components": [{"id": "x", "name": "A", "status": "operational", "group": False}]}
        self.assertEqual(len(parse_components(payload)), 1)

    def test_components_missing_is_empty_not_crash(self):
        self.assertEqual(parse_components({"page": {}}), ())


class SelectTests(unittest.TestCase):
    def setUp(self):
        self.comps = parse_components(KRAKEN)

    def test_selects_children_of_group(self):
        sel = select_exit(self.comps, Selector(groups=("Digital Currency Funding",)))
        self.assertEqual(sorted(c.name for c in sel), ["USDC (USDC) - Base", "USDC (USDC) - Solana"])

    def test_group_row_itself_not_a_signal(self):
        sel = select_exit(self.comps, Selector(groups=("Digital Currency Funding",)))
        self.assertNotIn("Digital Currency Funding", [c.name for c in sel])

    def test_name_pattern_selects_outside_groups(self):
        sel = select_exit(self.comps, Selector(patterns=(r"Wire Transfer",)))
        self.assertEqual([c.name for c in sel], ["Euro (EUR) - Wire Transfer Deposits"])

    def test_union_of_groups_and_patterns_is_deduplicated(self):
        sel = select_exit(self.comps, Selector(groups=("Digital Currency Funding",), patterns=(r"USDC",)))
        self.assertEqual(len(sel), 2)

    def test_no_match_is_empty_tuple(self):
        self.assertEqual(select_exit(self.comps, Selector(groups=("Nope",))), ())


class NetworkTests(unittest.TestCase):
    def test_kraken_suffix(self):
        self.assertEqual(network_from_name("USDC (USDC) - Base", "kraken_suffix"), "Base")

    def test_circle_usdc_chain(self):
        self.assertEqual(network_from_name("USDC - ARB - Redeeming", "circle_usdc"), "ARB")

    def test_unknown_rule_returns_none(self):
        self.assertIsNone(network_from_name("USDC - ARB - Redeeming", "nonexistent"))


if __name__ == "__main__":
    unittest.main()
