"""Tests for the Filesystem Sandbox."""
import os
import tempfile
from pathlib import Path
import pytest
from ai_agent_sandbox.fsandbox import FilesystemSandbox


class TestFilesystemSandbox:
    def test_allows_access_in_allowed_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sandbox = FilesystemSandbox(agent_id="test", allowed_dirs=[tmpdir])
            test_file = os.path.join(tmpdir, "test.py")
            assert sandbox.check_access(test_file, "read") is True
            assert sandbox.check_access(test_file, "write") is True

    def test_denies_access_outside_sandbox(self):
        sandbox = FilesystemSandbox(
            agent_id="test",
            allowed_dirs=["/home/user/projects"],
        )
        # writes/deletes outside allowed dirs should be denied
        assert sandbox.check_access("/etc/shadow", "write") is False
        assert sandbox.check_access("/root/secrets.txt", "delete") is False

    def test_violations_detected(self):
        sandbox = FilesystemSandbox(
            agent_id="test",
            allowed_dirs=["/home/user/projects"],
        )
        sandbox.check_access("/etc/shadow", "write")
        sandbox.check_access("/root/.ssh/id_rsa", "write")
        violations = sandbox.get_violations()
        assert len(violations) >= 2

    def test_events_logged(self):
        sandbox = FilesystemSandbox(
            agent_id="agent-1",
            allowed_dirs=["/home/user/projects"],
        )
        sandbox.check_access("/sensitive/file.txt", "write")
        events = sandbox.get_events()
        assert len(events) == 1
        assert events[0].allowed is False

    def test_allowed_dirs_list(self):
        sandbox = FilesystemSandbox(
            agent_id="test",
            allowed_dirs=["/home/user/projects", "/home/user/data"],
        )
        dirs = sandbox.allowed_dirs
        assert len(dirs) >= 2  # 2 explicit + tmp dirs

    def test_tmp_allowed_by_default(self):
        sandbox = FilesystemSandbox(
            agent_id="test",
            allowed_dirs=["/home/user/projects"],
        )
        assert sandbox.check_access("/tmp/agent-scratch.txt", "write") is True

    def test_deny_tmp(self):
        sandbox = FilesystemSandbox(
            agent_id="test",
            allowed_dirs=["/home/user/projects"],
            allow_tmp=False,
        )
        assert sandbox.check_access("/tmp/agent-scratch.txt", "write") is False

    def test_filter_events_by_operation(self):
        sandbox = FilesystemSandbox(
            agent_id="test",
            allowed_dirs=["/home/user/projects"],
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            sandbox.check_access(os.path.join(tmpdir, "a.txt"), "read")
            sandbox.check_access(os.path.join(tmpdir, "b.txt"), "write")
            reads = sandbox.get_events(operation="read")
            assert len(reads) == 1
