"""Tests for restrictbot CLI."""

import json
import sys
from pathlib import Path

import pytest

from restrictbot.cli import main


class TestCliCheck:
    def test_clean_product(self):
        sys.argv = ["restrictbot", "check", "Widget", "clean widget"]
        assert main() == 0

    def test_banned_product(self):
        sys.argv = ["restrictbot", "check", "AtlasBot", "humanoid robot"]
        assert main() == 0  # no --ci, so exit 0

    def test_banned_product_ci_fails(self):
        sys.argv = ["restrictbot", "check", "AtlasBot", "humanoid robot", "--ci"]
        assert main() == 1

    def test_restricted_product_ci_passes(self):
        # WARN is not FAIL, so CI should pass
        sys.argv = ["restrictbot", "check", "ExoBoost", "powered exoskeleton", "--ci"]
        assert main() == 0

    def test_json_output(self, capsys):
        sys.argv = ["restrictbot", "check", "Test", "humanoid robot", "--json"]
        assert main() == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["verdict"] == "fail"
        assert len(data["findings"]) >= 1

    def test_clean_json(self, capsys):
        sys.argv = ["restrictbot", "check", "Widget", "clean widget", "--json"]
        assert main() == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["verdict"] == "pass"


class TestCliCategories:
    def test_categories_listed(self, capsys):
        sys.argv = ["restrictbot", "categories"]
        assert main() == 0
        captured = capsys.readouterr()
        assert "BANNED" in captured.out
        assert "Humanoid Robot" in captured.out
        assert "Robot Dog" in captured.out
        assert "Solar Inverter" in captured.out


class TestCliScan:
    def test_scan_csv(self, tmp_path):
        csv_file = tmp_path / "products.csv"
        csv_file.write_text("name,description\nWidget,clean widget\nAtlasBot,humanoid robot\n")
        sys.argv = ["restrictbot", "scan", str(csv_file)]
        assert main() == 0

    def test_scan_csv_ci_fails(self, tmp_path):
        csv_file = tmp_path / "products.csv"
        csv_file.write_text("name,description\nAtlasBot,humanoid robot\n")
        sys.argv = ["restrictbot", "scan", str(csv_file), "--ci"]
        assert main() == 1

    def test_scan_csv_clean_ci_passes(self, tmp_path):
        csv_file = tmp_path / "products.csv"
        csv_file.write_text("name,description\nWidget,clean widget\n")
        sys.argv = ["restrictbot", "scan", str(csv_file), "--ci"]
        assert main() == 0

    def test_scan_csv_json(self, tmp_path, capsys):
        csv_file = tmp_path / "products.csv"
        csv_file.write_text("name,description\nWidget,clean widget\n")
        sys.argv = ["restrictbot", "scan", str(csv_file), "--json"]
        assert main() == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert len(data) == 1
        assert data[0]["verdict"] == "pass"

    def test_scan_missing_file(self):
        sys.argv = ["restrictbot", "scan", "/nonexistent/products.csv"]
        assert main() == 1

    def test_scan_empty_csv(self, tmp_path, capsys):
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("name,description\n")
        sys.argv = ["restrictbot", "scan", str(csv_file)]
        # No valid rows but no fail either
        assert main() == 0