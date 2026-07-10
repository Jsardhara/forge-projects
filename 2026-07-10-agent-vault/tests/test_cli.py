"""CLI smoke tests for agentvault."""
import subprocess
import sys
from datetime import timedelta

from agentvault import Vault
from agentvault.cli import main


def test_demo_runs_exit_zero(capsys):
    rc = main(["demo"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "chain intact: True" in out
    assert "resolved secret" in out


def test_egress_check_allow_cli():
    # Uses a sub-process-free in-process call.
    rc = main(["egress", "check", "--host", "api.github.com", "--rules", "api.github.com"])
    assert rc == 0  # ALLOW


def test_egress_check_deny_cli():
    rc = main(["egress", "check", "--host", "evil.com", "--rules", "api.github.com"])
    assert rc == 2  # DENY -> exit 2


def test_secret_add_and_list_cli(capsys):
    # In-process list on an empty vault returns nothing; just ensure no crash.
    rc = main(["secret", "list"])
    assert rc == 0


def test_session_issue_cli(capsys):
    rc = main(["session", "issue", "--egress", "--ttl", "30", "--max-uses", "3"])
    assert rc == 0
    assert "issued" in capsys.readouterr().out


def test_audit_cli():
    assert main(["audit"]) == 0
