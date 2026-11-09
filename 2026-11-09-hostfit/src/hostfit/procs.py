"""Who is currently holding the RAM.

When a workload does not fit in `MemAvailable`, the only useful next sentence
is "and here is who you would have to stop". This module reads that from
`/proc/<pid>/status`, never from a command line that could be wrong.
"""

import os
from dataclasses import dataclass, field

PROC_ROOT = "/proc"
KB = 1024


@dataclass(frozen=True)
class ProcInfo:
    pid: int
    comm: str
    rss: int


@dataclass(frozen=True)
class ProcessScan:
    procs: list = field(default_factory=list)
    unreadable: int = 0
    unmeasured_reason: str = None


def _read(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _rss_from_status(text):
    for line in text.splitlines():
        if line.startswith("VmRSS:"):
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                return int(parts[1]) * KB
    return None


def read_processes(root=PROC_ROOT):
    try:
        entries = os.listdir(root)
    except OSError as exc:
        return ProcessScan(unmeasured_reason="cannot list %s: %s" % (root, exc))

    procs = []
    unreadable = 0
    for entry in entries:
        if not entry.isdigit():
            continue
        pid = int(entry)
        try:
            comm = _read(os.path.join(root, entry, "comm")).strip()
            status = _read(os.path.join(root, entry, "status"))
        except OSError:
            # A process that exited between listdir and open is not an error,
            # but it is counted so the scan can say how complete it was.
            unreadable += 1
            continue
        rss = _rss_from_status(status)
        if rss is None:
            # Kernel threads have no VmRSS; they hold no user memory.
            continue
        procs.append(ProcInfo(pid=pid, comm=comm or "?", rss=rss))

    procs.sort(key=lambda p: (-p.rss, p.pid))
    return ProcessScan(procs=procs, unreadable=unreadable)


def largest_covering(procs, need):
    """Smallest prefix of the RSS-sorted list whose total reaches `need`.

    Returns None when stopping every listed process still would not free
    enough — that is a different answer from "stop these three".
    """
    if need <= 0:
        return []
    picked = []
    freed = 0
    for proc in procs:
        picked.append(proc)
        freed += proc.rss
        if freed >= need:
            return picked
    return None
