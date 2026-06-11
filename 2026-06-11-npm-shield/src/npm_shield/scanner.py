"""Core scanner — parse package-lock.json and identify install scripts."""
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from npm_shield.errors import InvalidLockfileError, LockfileNotFoundError

# npm lifecycle scripts that run automatically during install
_INSTALL_SCRIPTS = {"preinstall", "install", "postinstall", "prepare"}
# Scripts that only run on publish — NOT blocked by npm v12 allowScripts
_PUBLISH_ONLY_SCRIPTS = {"prepublish", "prepublishOnly", "postpublish"}


@dataclass
class PackageScriptInfo:
    """Information about a single package's scripts."""
    name: str
    version: str
    scripts: Dict[str, str]
    resolved: str = ""
    is_dev: bool = False
    is_optional: bool = False

    @property
    def is_install_script(self) -> bool:
        """True if this package has scripts that run during npm install."""
        return bool(set(self.scripts.keys()) & _INSTALL_SCRIPTS)

    @property
    def is_only_prepublish(self) -> bool:
        """True if this package only has publish-only scripts (safe for npm v12)."""
        non_publish = set(self.scripts.keys()) - _PUBLISH_ONLY_SCRIPTS
        return len(non_publish) == 0 and len(self.scripts) > 0


@dataclass
class ScanResult:
    """Result of scanning a project's lockfile."""
    project_name: str
    project_version: str
    lockfile_version: int
    total_packages: int
    packages_with_scripts: List[PackageScriptInfo]
    scan_path: str

    @property
    def packages_affected_by_v12(self) -> List[PackageScriptInfo]:
        """Packages whose install scripts will be BLOCKED by npm v12 defaults."""
        return [p for p in self.packages_with_scripts if p.is_install_script]

    def summary(self) -> str:
        affected = len(self.packages_affected_by_v12)
        total = self.total_packages
        return f"Found {affected} package(s) with install scripts out of {total} total."


def _parse_lockfile_v3(data: dict) -> dict:
    """Extract packages from a lockfileVersion 3 lockfile."""
    packages = data.get("packages")
    if not packages:
        raise InvalidLockfileError(
            "lockfileVersion 3 found but 'packages' key is missing."
        )
    return packages


def _parse_lockfile_v2(data: dict) -> dict:
    """Extract packages from a lockfileVersion 2 lockfile.

    v2 lockfiles may use either 'dependencies' (older) or 'packages' (newer v2 format).
    """
    deps = data.get("dependencies")
    if deps:
        return deps
    # Some v2 lockfiles use 'packages' key (transitional format)
    packages = data.get("packages")
    if packages:
        return packages
    raise InvalidLockfileError(
        "lockfileVersion 2 found but neither 'dependencies' nor 'packages' key is present."
    )


def _parse_lockfile_v1(data: dict) -> dict:
    """Extract packages from a lockfileVersion 1 lockfile."""
    deps = data.get("dependencies")
    if not deps:
        raise InvalidLockfileError(
            "lockfileVersion 1 found but 'dependencies' key is missing."
        )
    return deps


def _extract_packages(data: dict) -> dict:
    """Detect lockfile version and extract the packages dict."""
    version = data.get("lockfileVersion", 0)

    if version >= 3:
        packages = _parse_lockfile_v3(data)
    elif version == 2:
        packages = _parse_lockfile_v2(data)
    elif version == 1:
        packages = _parse_lockfile_v1(data)
    else:
        # Try v3 format first, then v2
        if "packages" in data:
            packages = data["packages"]
            version = 3
        elif "dependencies" in data:
            packages = data["dependencies"]
            version = 1
        else:
            raise InvalidLockfileError(
                "Unrecognized lockfile format. Expected 'packages' (v3) or "
                "'dependencies' (v1/v2) key."
            )

    return packages, version


def find_install_scripts(packages: dict) -> Dict[str, Dict[str, str]]:
    """Scan packages dict and return packages that have any scripts.

    Returns dict of {package_path: {script_name: script_command}}.
    """
    result = {}
    for path, info in packages.items():
        # Skip root entry
        if path == "":
            continue
        scripts = info.get("scripts")
        if scripts and isinstance(scripts, dict) and len(scripts) > 0:
            result[path] = scripts
    return result


def classify_risk(pkg_info: PackageScriptInfo) -> str:
    """Classify risk level for a package with install scripts.

    HIGH:  Multiple install scripts or known high-risk patterns
    MEDIUM: Single install script
    LOW:   Only publish-only scripts or prepare-only
    """
    install_scripts = set(pkg_info.scripts.keys()) & _INSTALL_SCRIPTS

    if len(install_scripts) >= 2:
        return "HIGH"
    elif len(install_scripts) == 1:
        return "MEDIUM"
    else:
        return "LOW"


def _is_dev_dependency(pkg_path: str, packages: dict) -> bool:
    """Heuristic: check if a package is likely a dev dependency."""
    # Check if it's in a devDependencies section of root
    root = packages.get("", {})
    deps = root.get("dependencies", {})
    dev_deps = root.get("devDependencies", {})

    # Extract the top-level package name (strip node_modules/ prefix)
    parts = pkg_path.replace("node_modules/", "").split("/")
    # Handle scoped packages like @types/node
    if parts[0].startswith("@"):
        pkg_name = "/".join(parts[:2]) if len(parts) > 2 else parts[0]
    else:
        pkg_name = parts[0]

    if pkg_name in dev_deps:
        return True
    if pkg_name in deps:
        return False
    return False


def scan_lockfile(lockfile_path: str) -> ScanResult:
    """Scan a package-lock.json and return structured results.

    Args:
        lockfile_path: Path to package-lock.json file.

    Returns:
        ScanResult with all findings.

    Raises:
        LockfileNotFoundError: If the file doesn't exist.
        InvalidLockfileError: If the file is malformed.
    """
    path = Path(lockfile_path)
    if not path.exists():
        raise LockfileNotFoundError(f"Lockfile not found: {lockfile_path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise InvalidLockfileError(f"Failed to parse lockfile: {e}")

    packages, version = _extract_packages(data)

    # Get project info from root entry
    root_entry = packages.get("", {})
    project_name = root_entry.get("name", "unknown")
    project_version = root_entry.get("version", "0.0.0")

    # Find all packages with scripts
    scripts_map = find_install_scripts(packages)

    # Build PackageScriptInfo objects
    pkg_infos: List[PackageScriptInfo] = []
    for pkg_path, scripts in scripts_map.items():
        # Extract name and version from path
        clean_path = pkg_path.replace("node_modules/", "")
        parts = clean_path.split("/")
        if parts[0].startswith("@"):
            name = "/".join(parts[:2]) if len(parts) > 2 else parts[0]
        else:
            name = parts[0]

        pkg_version = packages.get(pkg_path, {}).get("version", "?")
        resolved = packages.get(pkg_path, {}).get("resolved", "")
        is_dev = _is_dev_dependency(pkg_path, packages)

        info = PackageScriptInfo(
            name=name,
            version=pkg_version,
            scripts=scripts,
            resolved=resolved,
            is_dev=is_dev,
        )
        pkg_infos.append(info)

    # Sort by risk: HIGH first, then MEDIUM, then LOW
    risk_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    pkg_infos.sort(key=lambda p: risk_order.get(classify_risk(p), 3))

    return ScanResult(
        project_name=project_name,
        project_version=project_version,
        lockfile_version=version,
        total_packages=len([p for p in packages if p != ""]),
        packages_with_scripts=pkg_infos,
        scan_path=str(path.parent),
    )
