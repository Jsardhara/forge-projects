"""Discovery by path convention: <repo>/YYYY-MM-DD-<name>/src/<module>/cli.py."""

import datetime
import os
import re
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence

from .specs import DEFAULT_SPECS, VerifierSpec, spec_for  # noqa: F401

DATED_DIR = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-(.+)$")


@dataclass(frozen=True)
class Verifier:
    spec: VerifierSpec
    spec_path: str

    @property
    def name(self) -> str:
        return self.spec.name

    @property
    def src_dir(self) -> str:
        return os.path.join(self.spec_path, "src")


def project_name(dirname: str) -> Optional[str]:
    """`2026-11-02-cvewatch` -> `cvewatch`; anything not a real dated dir -> None."""
    match = DATED_DIR.match(dirname)
    if not match:
        return None
    year, month, day, slug = match.groups()
    try:
        datetime.date(int(year), int(month), int(day))
    except ValueError:
        return None
    return slug


def _module_dir(src_dir: str) -> Optional[str]:
    """The one package under src/ that exposes a cli module."""
    if not os.path.isdir(src_dir):
        return None
    for entry in sorted(os.listdir(src_dir)):
        if entry.startswith((".", "_")):
            continue
        if os.path.isfile(os.path.join(src_dir, entry, "cli.py")):
            return entry
    return None


def discover(
    root: str,
    only: Optional[Sequence[str]] = None,
    include_unknown: bool = False,
    exclude: Optional[Sequence[str]] = None,
) -> List[Verifier]:
    """The verifiers under `root`, sorted by name for deterministic reporting.

    By default only registered verifiers are returned. The repo contains many
    dated projects that ship a `cli.py` and are not verifiers; running those and
    labelling them `unmeasurable` would fill every report with noise, and noise is
    how a real transition gets missed. `include_unknown=True` opts them in.

    Raises OSError if `root` cannot be listed — the caller reports that as
    unmeasurable rather than pretending there was nothing to run.
    """
    entries = sorted(os.listdir(root))  # raises OSError on a bad path, by design
    wanted = set(only) if only else None
    blocked = set(exclude or ())
    found: List[Verifier] = []
    seen = set()
    for entry in entries:
        path = os.path.join(root, entry)
        if not os.path.isdir(path):
            continue
        name = project_name(entry)
        if name is None or name in blocked or name in seen:
            continue
        if wanted is not None:
            if name not in wanted:
                continue
        elif not include_unknown and name not in DEFAULT_SPECS:
            continue
        module = _module_dir(os.path.join(path, "src"))
        if module is None:
            continue
        found.append(Verifier(spec=spec_for(name, module, path), spec_path=path))
        seen.add(name)
    found.sort(key=lambda v: v.name)
    return found


def missing(only: Optional[Iterable[str]], found: Sequence[Verifier]) -> List[str]:
    """Names requested with --only that no directory provided."""
    if not only:
        return []
    present = {v.name for v in found}
    return [n for n in only if n not in present]
