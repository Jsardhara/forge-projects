"""Print the three exit paths of kcheck side by side, against fixtures.

    python3 demo_exit_paths.py     # exit 1 (this host) / 2 (unknown distro) / 0 (patched)

The first run is live (real probes). The other two replay recorded transcripts, because
this host cannot un-patch itself to demonstrate exit 0.
"""
import json
import os
import subprocess
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
KCHECK = os.path.join(ROOT, "kcheck")
SHIPPED = os.path.join(ROOT, "data", "fixed_versions.json")

FILES = {
    "uname.txt": "7.0.0-38-generic\n",
    "dpkg.txt": "linux-image-7.0.0-38-generic 7.0.0-38.38\nlinux-image-generic 7.0.0-38.38\n",
    "sysctl.txt": "net.mptcp.enabled = 1\n",
    "ss.txt": ("State  Recv-Q Send-Q  Local Address:Port  Peer Address:Port\n"
               "LISTEN 0      4096    127.0.0.1:42939       0.0.0.0:*\n"
               "LISTEN 0      4096    100.107.170.75:443    0.0.0.0:*\n"),
    "os-release.txt": 'ID=ubuntu\nVERSION_ID="26.04"\nVERSION_CODENAME=resolute\n',
}

PATCHED_FILES = {
    "uname.txt": "7.0.0-44-generic\n",
    "dpkg.txt": "linux-image-7.0.0-44-generic 7.0.0-44.44\n",
    "sysctl.txt": "net.mptcp.enabled = 0\n",
    "ss.txt": "State  Recv-Q Send-Q  Local Address:Port  Peer Address:Port\n",
}

UNKNOWN_DISTRO = {"os-release.txt": 'ID=arch\nPRETTY_NAME="Arch Linux"\n'}


def build(overrides, table=None):
    root = tempfile.mkdtemp(prefix="kcheck-demo-")
    files = dict(FILES)
    files.update(overrides)
    for name, content in files.items():
        with open(os.path.join(root, name), "w") as handle:
            handle.write(content)
    if table is not None:
        with open(os.path.join(root, "table.json"), "w") as handle:
            json.dump(table, handle)
    return root


def released_table():
    with open(SHIPPED) as handle:
        doc = json.load(handle)
    doc["cves"][0]["distros"]["ubuntu-26.04"]["fix_state"] = "released"
    return doc


def run(label, argv):
    proc = subprocess.run([KCHECK] + argv, capture_output=True, text=True)
    print("=" * 78)
    print("%s -> exit %d" % (label, proc.returncode))
    print("=" * 78)
    print(proc.stdout or proc.stderr)
    return proc.returncode


def main():
    codes = [run("LIVE (this host, real probes)", [])]
    codes.append(run("UNKNOWN DISTRO (arch fixture)", ["--fixtures", build(UNKNOWN_DISTRO)]))
    codes.append(run("PATCHED (7.0.0-44 fixture, released fix)",
                     ["--fixtures", build(PATCHED_FILES, table=released_table())]))
    print("=" * 78)
    print("exit codes exercised: %s" % codes)
    if codes != [1, 2, 0]:
        raise SystemExit("unexpected exit codes: %s" % codes)


if __name__ == "__main__":
    main()
