"""Agent bus integration for forge-scaffold."""

import sys
from pathlib import Path
from typing import Optional, Dict, Any

SCRIPTS_DIR = Path("C:/Users/jyot2/AppData/Local/hermes/scripts")


def _import_bus():
    """Import the bus module, returning None if unavailable."""
    try:
        sys.path.insert(0, str(SCRIPTS_DIR))
        from bus import publish, inbox, mark_read  # noqa: F401
        return {"publish": publish, "inbox": inbox, "mark_read": mark_read}
    except ImportError:
        return None


def publish_code_ready(
    project: str,
    tests: str,
    repo: str,
) -> bool:
    """Publish a code-ready message to the agent bus."""
    bus = _import_bus()
    if bus is None:
        print("Warning: agent bus not available, skipping publish")
        return False

    try:
        bus["publish"](
            topic="code-ready",
            from_agent="forge",
            to_agent="sentinel",
            data={
                "project": project,
                "tests": tests,
                "repo": repo,
            },
        )
        return True
    except Exception as e:
        print(f"Warning: bus publish failed: {e}")
        return False


def check_research() -> Optional[Dict[str, Any]]:
    """Check the agent bus for research-complete messages from Lens."""
    bus = _import_bus()
    if bus is None:
        print("Warning: agent bus not available")
        return None

    try:
        msgs = bus["inbox"]("forge", unread_only=True)
        for msg in msgs:
            if msg["topic"] == "research-complete":
                data = msg["data"]
                bus["mark_read"](msg["id"], "forge")
                return data
    except Exception as e:
        print(f"Warning: bus read failed: {e}")

    return None
