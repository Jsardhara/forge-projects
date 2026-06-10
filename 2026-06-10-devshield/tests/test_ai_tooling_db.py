"""Tests for the AI tooling database."""

from devshield.ai_tooling_db import is_ai_tooling, get_ai_packages, ALL_AI_PACKAGES


def test_is_ai_tooling_npm():
    assert is_ai_tooling("@anthropic-ai/claude-code", "npm") is True
    assert is_ai_tooling("openai", "npm") is True
    assert is_ai_tooling("langchain", "npm") is True


def test_is_ai_tooling_pip():
    assert is_ai_tooling("anthropic", "pip") is True
    assert is_ai_tooling("openai", "pip") is True
    assert is_ai_tooling("langchain", "pip") is True
    assert is_ai_tooling("google-generativeai", "pip") is True


def test_is_not_ai_tooling():
    assert is_ai_tooling("express", "npm") is False
    assert is_ai_tooling("flask", "pip") is False
    assert is_ai_tooling("django", "pip") is False


def test_is_ai_tooling_case_insensitive():
    assert is_ai_tooling("OpenAI", "npm") is True
    assert is_ai_tooling("ANTHROPIC", "pip") is True


def test_get_ai_packages():
    npm_pkgs = get_ai_packages("npm")
    assert "@anthropic-ai/claude-code" in npm_pkgs
    assert "openai" in npm_pkgs

    pip_pkgs = get_ai_packages("pip")
    assert "anthropic" in pip_pkgs
    assert "openai" in pip_pkgs


def test_get_ai_packages_unknown_ecosystem():
    assert get_ai_packages("gem") == []


def test_all_ai_packages_not_empty():
    assert len(ALL_AI_PACKAGES) > 0
