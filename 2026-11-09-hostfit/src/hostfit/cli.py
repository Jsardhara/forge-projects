"""CLI: `hostfit --peak-gib N` or `hostfit --requirement req.json`."""

import argparse
import json
import os
import sys

from .meminfo import MEMINFO_PATH, snapshot_from_path
from .procs import PROC_ROOT, largest_covering, read_processes
from .verdict import GIB, Requirement, evaluate

SHM_PATH = "/dev/shm"


def _load_requirement(path):
    with open(path, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
    name = payload.get("name") or os.path.splitext(os.path.basename(path))[0]
    peak = payload.get("peak_gib")
    if not isinstance(peak, (int, float)) or peak <= 0:
        raise ValueError("requirement needs a positive numeric peak_gib")
    return Requirement(
        name=name,
        peak_bytes=int(peak * GIB),
        shm_bytes=int(float(payload.get("shm_gib") or 0) * GIB),
        headroom_pct=float(payload.get("headroom_pct", 10.0)),
    )


def _shm_available(path=SHM_PATH):
    try:
        st = os.statvfs(path)
    except OSError:
        return None
    return st.f_bavail * st.f_frsize


def _payload(verdict, snapshot, scan, picked, top):
    req = verdict.requirement
    return {
        "state": verdict.state,
        "exit_code": verdict.exit_code,
        "requirement": {
            "name": req.name,
            "peak_gib": round(req.peak_bytes / GIB, 3),
            "shm_gib": round(req.shm_bytes / GIB, 3),
            "headroom_pct": req.headroom_pct,
        },
        "snapshot": {
            "available_gib": None if snapshot.available is None else round(snapshot.available / GIB, 3),
            "total_gib": None if snapshot.total is None else round(snapshot.total / GIB, 3),
            "swap_free_gib": None if snapshot.swap_free is None else round(snapshot.swap_free / GIB, 3),
            "unmeasured_reason": snapshot.unmeasured_reason,
        },
        "margin_gib": None if verdict.margin is None else round(verdict.margin / GIB, 3),
        "reclaim_needed_gib": round(verdict.reclaim_needed / GIB, 3),
        "reasons": verdict.reasons,
        "top_consumers": [
            {"pid": p.pid, "comm": p.comm, "rss_gib": round(p.rss / GIB, 3)}
            for p in list(scan.procs)[:top]
        ],
        "stop_these_to_fit": [] if picked is None else [p.comm for p in picked],
        "reclaim_closable": picked is not None,
        "processes_unreadable": scan.unreadable,
    }


def _render(payload):
    lines = [
        "hostfit: %s" % payload["requirement"]["name"],
        "  state            : %s" % payload["state"],
        "  available / total: %s / %s GiB"
        % (payload["snapshot"]["available_gib"], payload["snapshot"]["total_gib"]),
        "  required         : %s GiB (headroom %s%%)"
        % (payload["requirement"]["peak_gib"], payload["requirement"]["headroom_pct"]),
        "  reclaim needed   : %s GiB" % payload["reclaim_needed_gib"],
    ]
    for reason in payload["reasons"]:
        lines.append("  - %s" % reason)
    if payload["top_consumers"]:
        lines.append("  top RSS holders:")
        for proc in payload["top_consumers"]:
            lines.append("    %6d  %-20s %s GiB" % (proc["pid"], proc["comm"], proc["rss_gib"]))
    if payload["state"] == "BLOCKED_NOW":
        if payload["reclaim_closable"]:
            lines.append("  stop to fit: %s" % ", ".join(payload["stop_these_to_fit"]))
        else:
            lines.append("  stop to fit: not closable from user processes alone")
    return "\n".join(lines)


def build_parser():
    p = argparse.ArgumentParser(prog="hostfit", description=__doc__)
    p.add_argument("--peak-gib", type=float, help="peak RSS the workload needs")
    p.add_argument("--shm-gib", type=float, default=0.0, help="/dev/shm this workload needs")
    p.add_argument("--requirement", help="JSON file: {name, peak_gib, shm_gib?, headroom_pct?}")
    p.add_argument("--headroom-pct", type=float, default=10.0)
    p.add_argument("--top", type=int, default=5, help="how many RSS holders to list")
    p.add_argument("--json", action="store_true")
    p.add_argument("--meminfo", default=MEMINFO_PATH)
    p.add_argument("--procroot", default=PROC_ROOT)
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.requirement:
        try:
            requirement = _load_requirement(args.requirement)
        except (OSError, ValueError) as exc:
            print("hostfit: cannot use requirement %s: %s" % (args.requirement, exc), file=sys.stderr)
            return 2
        if args.peak_gib:
            print("hostfit: --peak-gib ignored, requirement file wins", file=sys.stderr)
    elif args.peak_gib:
        requirement = Requirement(
            name="cli",
            peak_bytes=int(args.peak_gib * GIB),
            shm_bytes=int(args.shm_gib * GIB),
            headroom_pct=args.headroom_pct,
        )
    else:
        parser.error("one of --peak-gib or --requirement is required")

    snapshot = snapshot_from_path(args.meminfo)
    scan = read_processes(args.procroot)
    verdict = evaluate(snapshot, requirement, shm_available=_shm_available())
    picked = largest_covering(scan.procs, verdict.reclaim_needed) if verdict.reclaim_needed else []
    payload = _payload(verdict, snapshot, scan, picked, max(args.top, 0))

    print(json.dumps(payload, indent=2) if args.json else _render(payload))
    return verdict.exit_code
