"""Filesystem Sandbox — Monitoring and restricting file access for AI agents.

Provides a sandboxed view of the filesystem where agents can be restricted
to specific directories. Logs all file access attempts for audit.
"""

from __future__ import annotations

import os
import time
import threading
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FileAccessEvent:
    """Record of a file access attempt."""
    timestamp: float
    path: str
    operation: str  # "read", "write", "delete", "list"
    allowed: bool
    agent_id: str = "default"
    reason: str = ""


class FilesystemSandbox:
    """Restricts and monitors filesystem access for AI agents.

    Agents are confined to a set of allowed directories.
    All access attempts are logged for audit.

    Usage:
        sandbox = FilesystemSandbox(
            agent_id="claude-code-1",
            allowed_dirs=["/home/user/projects/myapp"],
        )
        sandbox.check_access("/home/user/projects/myapp/src/main.py", "read")  # True
        sandbox.check_access("/etc/passwd", "read")  # False
    """

    def __init__(
        self,
        agent_id: str = "default",
        allowed_dirs: list[str] | None = None,
        allow_tmp: bool = True,
    ) -> None:
        self._agent_id = agent_id
        self._allow_tmp = allow_tmp
        self._events: list[FileAccessEvent] = []
        self._lock = threading.Lock()

        # Resolve allowed directories
        self._allowed_dirs: list[Path] = []
        if allowed_dirs:
            for d in allowed_dirs:
                p = Path(d).resolve()
                self._allowed_dirs.append(p)

        # Always allow /tmp by default (agents need scratch space)
        if allow_tmp:
            self._allowed_dirs.append(Path("/tmp").resolve())
            # On Windows, also allow the temp directory
            if "TEMP" in os.environ:
                self._allowed_dirs.append(Path(os.environ["TEMP"]).resolve())
            if "TMP" in os.environ:
                self._allowed_dirs.append(Path(os.environ["TMP"]).resolve())

    def check_access(self, path: str, operation: str = "read") -> bool:
        """Check if a file operation is allowed.

        Args:
            path: The file path being accessed.
            operation: Type of access — "read", "write", "delete", "list".

        Returns:
            True if the operation is allowed.
        """
        p = Path(path).resolve()

        # Check if the path is within any allowed directory
        allowed = False
        for allowed_dir in self._allowed_dirs:
            try:
                p.relative_to(allowed_dir)
                allowed = True
                break
            except ValueError:
                continue

        # Special: allow reads from /usr, /lib, etc. (system libs)
        if not allowed and operation == "read":
            system_prefixes = ["/usr", "/lib", "/etc/ssl", "/etc/resolv.conf"]
            for prefix in system_prefixes:
                try:
                    p.relative_to(Path(prefix))
                    allowed = True
                    break
                except ValueError:
                    continue

        event = FileAccessEvent(
            timestamp=time.time(),
            path=str(p),
            operation=operation,
            allowed=allowed,
            agent_id=self._agent_id,
            reason="within_allowed_dir" if allowed else "outside_sandbox",
        )
        with self._lock:
            self._events.append(event)

        return allowed

    def get_events(self, operation: str = "") -> list[FileAccessEvent]:
        """Get file access events, optionally filtered by operation."""
        with self._lock:
            events = list(self._events)
        if operation:
            events = [e for e in events if e.operation == operation]
        return events

    def get_violations(self) -> list[FileAccessEvent]:
        """Get all denied access attempts."""
        with self._lock:
            return [e for e in self._events if not e.allowed]

    @property
    def allowed_dirs(self) -> list[str]:
        """Return the list of allowed directories."""
        return [str(d) for d in self._allowed_dirs]
