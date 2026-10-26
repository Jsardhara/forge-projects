"""Local runtime inventory.

Everything here is a read-only probe of the machine the tool runs on. Nothing is
installed, fetched, or executed from the scanned tree; interpreters are asked a
single question in their own process because a module's version in *that*
interpreter is the only version that can actually load there.

Every probe failure is surfaced as an error field rather than a silent absence --
"could not determine" and "not installed" are different answers.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

__all__ = [
    "PROBE_SOURCE",
    "NodeInstall",
    "PythonInstall",
    "SystemPackage",
    "SubprocessRunner",
    "find_node",
    "find_pythons",
    "find_system_packages",
    "discover_python_paths",
    "parse_debian_version_line",
    "parse_deb822_line",
]

# Runs inside the target interpreter. Reports the version of any Brotli binding
# that is importable there, falling back to installed-distribution metadata when
# the module does not expose __version__ (brotlicffi does not, historically).
PROBE_SOURCE = r"""
import json, sys
payload = {"executable": sys.executable,
           "version": "%d.%d.%d" % tuple(sys.version_info[:3]),
           "modules": {}}
try:
    from importlib import metadata as importlib_metadata
except Exception:  # pragma: no cover - python < 3.8 has no importlib.metadata
    importlib_metadata = None
for name in ("brotli", "Brotli", "brotlicffi", "_brotli"):
    try:
        module = __import__(name)
    except Exception:
        continue
    version = getattr(module, "__version__", None)
    if version is None and importlib_metadata is not None:
        for dist in (name, name.lower(), name.capitalize()):
            try:
                version = importlib_metadata.version(dist)
                break
            except Exception:
                continue
    payload["modules"][name] = {"version": version,
                                "file": getattr(module, "__file__", None)}
print(json.dumps(payload))
"""


@dataclass(frozen=True)
class NodeInstall:
    path: str
    version: Optional[str]
    error: Optional[str] = None


@dataclass(frozen=True)
class PythonInstall:
    path: str
    version: Optional[str]
    modules: Dict[str, Dict] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass(frozen=True)
class SystemPackage:
    name: str
    version: str
    manager: str


class SubprocessRunner:
    """The only place this package spawns a process."""

    def run(self, argv, timeout=10.0, cwd=None):
        return subprocess.run(
            list(argv),
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            check=False,
        )


def _text(result) -> str:
    return getattr(result, "stdout", "") or ""


def _err(result) -> str:
    return (getattr(result, "stderr", "") or "").strip()


def _rc(result) -> int:
    return int(getattr(result, "returncode", 0))


def find_node(runner, timeout: float = 10.0) -> List[NodeInstall]:
    """Every ``node``/``nodejs`` on PATH, with the version that binary reports."""
    found = runner.run(["which", "-a", "node", "nodejs"], timeout=timeout)
    paths = [line.strip() for line in _text(found).splitlines() if line.strip()]
    installs: List[NodeInstall] = []
    for path in _unique(paths):
        result = runner.run([path, "--version"], timeout=timeout)
        if _rc(result) != 0:
            installs.append(NodeInstall(path, None, "node --version failed: %s" % _err(result)))
            continue
        raw = _text(result).strip()
        version = raw[1:] if raw[:1] in ("v", "V") else raw
        if not version or not version[0].isdigit():
            installs.append(NodeInstall(path, None, "unparsable node version %r" % raw))
            continue
        installs.append(NodeInstall(path, version, None))
    return installs


def discover_python_paths(runner, extras: Optional[Iterable[str]] = None,
                          timeout: float = 10.0) -> List[str]:
    """Explicit interpreter paths first, then whatever PATH advertises."""
    ordered: List[str] = [path for path in (extras or []) if path]
    found = runner.run(["which", "-a", "python3"], timeout=timeout)
    ordered.extend(line.strip() for line in _text(found).splitlines() if line.strip())
    return _unique(ordered)


def find_pythons(runner, paths: Iterable[str], timeout: float = 20.0) -> List[PythonInstall]:
    installs: List[PythonInstall] = []
    for path in paths:
        result = runner.run([path, "-c", PROBE_SOURCE], timeout=timeout)
        if _rc(result) != 0:
            detail = _err(result) or "exit %d" % _rc(result)
            installs.append(PythonInstall(path, None, {}, "probe failed: %s" % detail))
            continue
        try:
            payload = json.loads(_text(result))
        except (ValueError, TypeError) as exc:
            installs.append(
                PythonInstall(path, None, {}, "probe returned unparsable output: %s" % exc)
            )
            continue
        if not isinstance(payload, dict):
            installs.append(PythonInstall(path, None, {}, "probe returned a non-object payload"))
            continue
        modules = payload.get("modules") or {}
        if not isinstance(modules, dict):
            modules = {}
        installs.append(
            PythonInstall(path, payload.get("version"), modules, None)
        )
    return installs


def find_system_packages(runner, names: Iterable[str], timeout: float = 10.0) -> List[SystemPackage]:
    """Distribution packages that provide the decoder, via dpkg then rpm."""
    wanted = [str(name) for name in names]
    packages = _dpkg_packages(runner, wanted, timeout)
    if packages:
        return packages
    return _rpm_packages(runner, wanted, timeout)


def _dpkg_packages(runner, wanted: List[str], timeout: float) -> List[SystemPackage]:
    result = runner.run(
        ["dpkg-query", "-W", "-f=${Package}\t${Version}\n"] + wanted, timeout=timeout
    )
    if _rc(result) not in (0, 1):
        return []
    packages: List[SystemPackage] = []
    for line in _text(result).splitlines():
        parsed = parse_deb822_line(line)
        if parsed is None:
            continue
        name, version = parsed
        if name.split(":")[0] in wanted:
            packages.append(SystemPackage(name, version, "dpkg"))
    return packages


def parse_debian_version_line(line: str):
    """Legacy ``dpkg -l`` shape: ``ii  name  version  arch  description``."""
    fields = line.split()
    if len(fields) < 3:
        return None
    return fields[1], fields[2]


def parse_deb822_line(line: str):
    """``dpkg-query -W`` shape: ``name<TAB>version``."""
    if "\t" not in line:
        return None
    name, version = line.split("\t", 1)
    name, version = name.strip(), version.strip()
    if not name or not version:
        return None
    return name, version


def _rpm_packages(runner, wanted: List[str], timeout: float) -> List[SystemPackage]:
    result = runner.run(["rpm", "-q"] + wanted, timeout=timeout)
    if _rc(result) != 0:
        return []
    packages: List[SystemPackage] = []
    for line in _text(result).splitlines():
        parsed = _parse_rpm_line(line.strip(), wanted)
        if parsed is not None:
            packages.append(SystemPackage(parsed[0], parsed[1], "rpm"))
    return packages


def _parse_rpm_line(line: str, wanted: List[str]):
    if not line or " " in line and "is not installed" in line:
        return None
    body = line.rsplit(".", 1)[0] if "." in line else line  # drop the arch suffix
    for name in wanted:
        if body == name:
            return name, ""
        prefix = name + "-"
        if body.startswith(prefix):
            rest = body[len(prefix):]
            return name, rest
    return None


def _unique(items: Iterable[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def which_all(name: str) -> List[str]:
    """Convenience for callers that want PATH lookup without a runner."""
    located = shutil.which(name)
    return [located] if located else []
