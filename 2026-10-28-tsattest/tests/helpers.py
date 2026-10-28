"""Shared builders for tsattest tests (stdlib only)."""

import json
import os
import tempfile


PREFS_SSH_ON = json.dumps({"RunSSH": True, "WantRunning": True, "LoggedOut": False})

PREFS_SSH_OFF = json.dumps({"RunSSH": False, "WantRunning": True, "LoggedOut": False})


def status_doc(ssh_host_keys=None, backend_state="Running", version="1.102.3-t9329c3677-ga522f65e9"):
    """Build a tailscale status --json document with the real shape observed on this host."""
    self_node = {
        "ID": "n1",
        "HostName": "jarmes",
        "DNSName": "jarmes.taildfb99c.ts.net.",
        "OS": "linux",
        "Online": True,
        "TailscaleIPs": ["100.107.170.75"],
        "InNetworkMap": True,
    }
    if ssh_host_keys is not None:
        self_node["SSH_HostKeys"] = ssh_host_keys
    return {
        "Version": version,
        "ClientVersion": version,
        "BackendState": backend_state,
        "HaveNodeKey": True,
        "Self": self_node,
        "Peer": {
            "p1": {"HostName": "laptop", "OS": "windows", "Online": True},
            "p2": {"HostName": "phone", "OS": "android", "Online": False},
        },
        "User": {"918733619028434": {"ID": 918733619028434, "LoginName": "owner@github"}},
    }


def write_fixtures(root, version="1.102.3", prefs=None, status=None, serve=None,
                   environ=None, defaults=None):
    """Lay out a fixture directory. A None argument means 'this probe has no fixture'."""
    os.makedirs(root, exist_ok=True)
    if version is not None:
        with open(os.path.join(root, "version.txt"), "w") as fh:
            fh.write("%s\n  tailscale commit: 9329c3677031109ff6d0b80abee0cddc8f35ff6f\n"
                     "  long version: %s-t9329c3677-ga522f65e9\n" % (version, version))
    if prefs is not None:
        with open(os.path.join(root, "prefs.json"), "w") as fh:
            fh.write(prefs)
    if status is not None:
        with open(os.path.join(root, "status.json"), "w") as fh:
            fh.write(json.dumps(status if isinstance(status, dict) else json.loads(status)))
    if serve is not None:
        with open(os.path.join(root, "serve.txt"), "w") as fh:
            fh.write(serve)
    if environ is not None:
        with open(os.path.join(root, "environ.txt"), "w") as fh:
            fh.write(environ)
    if defaults is not None:
        with open(os.path.join(root, "defaults.txt"), "w") as fh:
            fh.write(defaults)
    return root


def tempdir():
    return tempfile.mkdtemp(prefix="tsattest-test-")
