"""Shared builders for kcheck tests (stdlib only).

Every fixture here is a *transcript* of a real probe, so the parsers are tested
against the shape the host actually emits rather than a shape we invented.
"""

import json
import os
import tempfile

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHIPPED_TABLE = os.path.join(PROJECT_ROOT, "data", "fixed_versions.json")

# dpkg-query -W -f='${Package} ${Version}\n' 'linux-image-*' on this host, 2026-11-01.
# The blank-version lines are real: two packages are in a half-installed state and
# dpkg prints an empty version for them. A parser that assumes two fields crashes here.
DPKG_REAL = """\
linux-image-7.0.0-30-generic \n\
linux-image-7.0.0-31-generic 7.0.0-31.31\n\
linux-image-7.0.0-34-generic 7.0.0-34.34\n\
linux-image-7.0.0-38-generic 7.0.0-38.38\n\
linux-image-fb-generic \n\
linux-image-generic 7.0.0-38.38\n\
linux-image-unsigned-7.0.0-30-generic 7.0.0-30.30\n\
linux-image-unsigned-7.0.0-31-generic \n\
linux-image-unsigned-7.0.0-34-generic \n\
linux-image-unsigned-7.0.0-38-generic \n\
"""

# ss -Mln on this host, 2026-11-01: five MPTCP listeners, all on localhost or tailnet.
SS_TAILNET = """\
State  Recv-Q Send-Q               Local Address:Port  Peer Address:Port
LISTEN 0      4096                100.107.170.75:45480      0.0.0.0:*
LISTEN 0      4096                     127.0.0.1:42939      0.0.0.0:*
LISTEN 0      4096                100.107.170.75:443        0.0.0.0:*
LISTEN 0      4096   [fd7a:115c:a1e0::c42d:aa4c]:443           [::]:*
LISTEN 0      4096   [fd7a:115c:a1e0::c42d:aa4c]:54649         [::]:*
"""

SS_EMPTY = """\
State  Recv-Q Send-Q               Local Address:Port  Peer Address:Port
"""

SS_PUBLIC = """\
State  Recv-Q Send-Q               Local Address:Port  Peer Address:Port
LISTEN 0      4096                            0.0.0.0:8080       0.0.0.0:*
LISTEN 0      4096                       203.0.113.9:443        0.0.0.0:*
"""

OS_UBUNTU_2604 = 'ID=ubuntu\nVERSION_ID="26.04"\nVERSION_CODENAME=resolute\nPRETTY_NAME="Ubuntu 26.04.1 LTS"\n'

OS_ARCH = 'ID=arch\nPRETTY_NAME="Arch Linux"\n'


def _table_row(fix_state="pending", fixed_version="7.0.0-43.43", retrieved_at="2026-11-01T06:26:00Z"):
    return {
        "cve": "CVE-2026-98432",
        "title": "Linux IPv4 TCP use-after-free on the MPTCP path",
        "cvss": 9.8,
        "cvss_vector": "AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "published": "2026-10-15",
        "introduced": "4.4",
        "fixed_branches": {"6.6": "6.6.159", "7.2": "7.2.10"},
        "attack_path": {"probe": "ss -Mln", "label": "MPTCP listener reachable from a remote peer"},
        "mitigation": {"summary": "u32 drop rule", "pointer": "outputs/lens-daily-intel.md", "automated": False},
        "distros": {
            "ubuntu-26.04": {
                "distro": "ubuntu",
                "release": "26.04",
                "codename": "resolute",
                "fix_state": fix_state,
                "fixed_version": fixed_version,
                "status_text": "Vulnerable -- work in progress in 7.0.0-43.43",
                "source_url": "https://ubuntu.com/security/CVE-2026-98432",
                "retrieved_at": retrieved_at,
            }
        },
    }


def table_doc(**row_kwargs):
    return {
        "schema_version": 1,
        "generated_at": "2026-11-01T06:26:00Z",
        "stale_after_days": 7,
        "cves": [_table_row(**row_kwargs)],
    }


def write_fixtures(root, uname="7.0.0-38-generic\n", dpkg=DPKG_REAL, sysctl="net.mptcp.enabled = 1\n",
                   ss=SS_TAILNET, os_release=OS_UBUNTU_2604, table=None):
    """Lay out a probe-fixture directory. None for any argument means 'probe unavailable'."""
    os.makedirs(root, exist_ok=True)
    files = {
        "uname.txt": uname,
        "dpkg.txt": dpkg,
        "sysctl.txt": sysctl,
        "ss.txt": ss,
        "os-release.txt": os_release,
    }
    for name, content in files.items():
        if content is None:
            continue
        with open(os.path.join(root, name), "w") as fh:
            fh.write(content)
    if table is not None:
        with open(os.path.join(root, "table.json"), "w") as fh:
            if isinstance(table, str):
                fh.write(table)
            else:
                json.dump(table, fh)
    return root


def tempdir():
    return tempfile.mkdtemp(prefix="kcheck-test-")


def fixtures(**kwargs):
    return write_fixtures(tempdir(), **kwargs)
