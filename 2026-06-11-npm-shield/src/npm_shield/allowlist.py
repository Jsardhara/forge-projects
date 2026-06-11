"""Generate npm v12-compliant allowlist configuration."""
from typing import Dict, List

from npm_shield.scanner import ScanResult


def generate_allowlist(scan_result: ScanResult) -> Dict[str, List[str]]:
    """Generate npm v12 'authorization' config from scan results.

    Returns a dict suitable for insertion into package.json:
    {
        "authorization": {
            "authorizedPackages": {
                "package-name": ["script-name", ...],
                ...
            }
        }
    }
    """
    authorized = {}

    for pkg in scan_result.packages_affected_by_v12:
        install_scripts = [
            name for name in pkg.scripts
            if name in {"preinstall", "install", "postinstall", "prepare"}
        ]
        if install_scripts:
            authorized[f"{pkg.name}@{pkg.version}"] = install_scripts

    return {
        "authorization": {
            "authorizedPackages": authorized
        }
    }


def generate_allowlist_json(scan_result: ScanResult, indent: int = 2) -> str:
    """Generate a JSON string for the allowlist configuration."""
    import json
    return json.dumps(generate_allowlist(scan_result), indent=indent)
