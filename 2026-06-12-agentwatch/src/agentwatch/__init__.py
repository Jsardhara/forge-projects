"""AgentWatch — AI Agent Cost & Guardrail Monitoring."""

__version__ = "0.1.0"

from pathlib import Path
import os

DEFAULT_DB_PATH = Path(os.environ.get("AGENTWATCH_DB_PATH", "agentwatch.db"))
