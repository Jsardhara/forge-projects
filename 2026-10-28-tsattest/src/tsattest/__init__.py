"""tsattest -- is the Tailscale SSH mitigation actually loaded in the running process?"""

__version__ = "1.0.0"

from . import bulletins, cli, collect, report, semver  # noqa: F401

__all__ = ["bulletins", "cli", "collect", "report", "semver", "__version__"]
