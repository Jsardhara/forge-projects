"""Tests for restrictbot scanner."""

import pytest

from restrictbot.scanner import scan_product, available_categories, scan_products


class TestAvailableCategories:
    def test_has_categories(self):
        cats = available_categories()
        assert len(cats) >= 5

    def test_has_banned_categories(self):
        cats = available_categories()
        banned = [c for c in cats if c.level.value == "banned"]
        assert len(banned) >= 3

    def test_has_humanoid(self):
        cats = available_categories()
        slugs = [c.slug for c in cats]
        assert "humanoid_robot" in slugs

    def test_has_robot_dog(self):
        cats = available_categories()
        slugs = [c.slug for c in cats]
        assert "robot_dog" in slugs

    def test_has_solar_inverter(self):
        cats = available_categories()
        slugs = [c.slug for c in cats]
        assert "solar_inverter" in slugs


class TestScanProduct:
    def test_clean_product_passes(self):
        result = scan_product("Widget Pro", "A general-purpose industrial sensor module")
        assert result.verdict.value == "pass"
        assert result.score == 0.0

    def test_humanoid_robot_fails(self):
        result = scan_product("AtlasBot", "Next-generation humanoid robot for warehouse automation")
        assert result.verdict.value == "fail"
        assert result.score >= 0.9

    def test_robot_dog_fails(self):
        result = scan_product("Spot Pro", "Rugged robot dog for inspection and monitoring")
        assert result.verdict.value == "fail"
        assert result.score >= 0.9

    def test_solar_inverter_fails(self):
        result = scan_product("SunPower X1", "High-efficiency solar inverter for residential use")
        assert result.verdict.value == "fail"
        assert result.score >= 0.9

    def test_exoskeleton_warns(self):
        result = scan_product("ExoBoost", "Powered exoskeleton for industrial workers")
        assert result.verdict.value == "warn"
        assert result.score >= 0.5

    def test_ugv_warns(self):
        result = scan_product("MuleBot", "Autonomous ground vehicle for logistics")
        assert result.verdict.value == "warn"
        assert result.score >= 0.5

    def test_multiple_categories_finds_all(self):
        result = scan_product("MegaBot", "Humanoid robot dog with solar inverter")
        assert result.verdict.value == "fail"
        categories = [f.category for f in result.findings]
        assert "humanoid_robot" in categories
        assert "robot_dog" in categories
        assert "solar_inverter" in categories

    def test_keyword_variants_detected(self):
        result = scan_product("QuadBot", "A biomimetic quadruped robot for search and rescue")
        assert result.verdict.value == "fail"  # robot dog + biomimetic

    def test_description_with_negation_still_matches(self):
        # Even if the text says "not a humanoid robot", the keyword "humanoid robot"
        # still appears in the text. This is a compliance scanner, not a sentiment analyzer.
        result = scan_product("SafeBot", "This is not a humanoid robot, it's a toy")
        assert result.verdict.value == "fail"

    def test_case_insensitive_matching(self):
        result = scan_product("test", "HUMANOID ROBOT")
        assert result.verdict.value == "fail"

    def test_telepresence_restricted(self):
        result = scan_product("TeleBot", "Remote presence robot for healthcare")
        assert result.verdict.value == "warn"

    def test_biomimetic_restricted(self):
        result = scan_product("SnakeBot", "Bio-inspired snake robot for pipeline inspection")
        assert result.verdict.value == "warn"

    def test_empty_description_passes(self):
        result = scan_product("Widget", "")
        assert result.verdict.value == "pass"


class TestScanProducts:
    def test_multiple_products(self):
        products = [
            ("Widget", "Simple widget"),
            ("AtlasBot", "Humanoid robot"),
            ("ExoBoost", "Powered exoskeleton"),
        ]
        results = scan_products(products)
        assert len(results) == 3
        assert results[0].verdict.value == "pass"
        assert results[1].verdict.value == "fail"
        assert results[2].verdict.value == "warn"

    def test_empty_list(self):
        results = scan_products([])
        assert results == []


class TestToDict:
    def test_result_to_dict(self):
        result = scan_product("Test", "Humanoid robot")
        d = result.to_dict()
        assert "product_name" in d
        assert "verdict" in d
        assert "findings" in d
        assert "score" in d

    def test_clean_result_to_dict(self):
        result = scan_product("Test", "clean widget")
        d = result.to_dict()
        assert d["verdict"] == "pass"
        assert len(d["findings"]) == 0