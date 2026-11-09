"""Read the kernel's own view of physical memory.

The whole point of this module is to refuse vendor-spec numbers: `MemTotal` is
what the kernel sees after firmware reservations, and `MemAvailable` is what a
new process can actually get *now* without swapping. Both come from
`/proc/meminfo` or not at all.
"""

from dataclasses import dataclass

MEMINFO_PATH = "/proc/meminfo"
KB = 1024


@dataclass(frozen=True)
class MemorySnapshot:
    total: int = None
    available: int = None
    swap_free: int = None
    unmeasured_reason: str = None

    @property
    def measured(self):
        return self.unmeasured_reason is None


def parse_meminfo(text):
    """Return {field: bytes} for every `<Name>: <n> kB` line.

    Lines without the `kB` unit are dropped rather than guessed at: a bare
    integer in this file is not a byte count.
    """
    values = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, _, raw = line.partition(":")
        parts = raw.split()
        if len(parts) != 2 or parts[1] != "kB":
            continue
        try:
            values[key.strip()] = int(parts[0]) * KB
        except ValueError:
            continue
    return values


def snapshot_from_text(text):
    values = parse_meminfo(text)
    missing = [f for f in ("MemTotal", "MemAvailable") if f not in values]
    if missing:
        return MemorySnapshot(unmeasured_reason="missing %s in meminfo" % " and ".join(missing))
    return MemorySnapshot(
        total=values["MemTotal"],
        available=values["MemAvailable"],
        swap_free=values.get("SwapFree"),
    )


def snapshot_from_path(path=MEMINFO_PATH):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError as exc:
        return MemorySnapshot(unmeasured_reason="cannot read %s: %s" % (path, exc))
    return snapshot_from_text(text)
