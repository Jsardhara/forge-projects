"""Baseline state: normalise a verifier's signal, save it atomically, diff it.

The normalisation exists because the alternative is noise. Four of these five tools
print a timestamp on every run; without stripping volatile tokens the digest would
change every single morning and "TRANSITION" would fire on nothing for a week.
"""

import hashlib
import json
import os
import re
from typing import Dict, Iterable, List, Optional

from .models import VerifierResult, Transition

SCHEMA = 1

_ISO_TS = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?")
_DURATION = re.compile(r"\b\d+(?:\.\d+)?\s?(?:s|ms|sec|secs|seconds)\b")


def normalize_signal(text: str, extra: Iterable[str] = ()) -> str:
    """Drop volatile tokens so only a real change moves the digest.

    `extra` carries per-verifier patterns for counters that are not verdicts.
    A malformed pattern is skipped rather than raising: a bad registry entry must
    not take the whole morning's posture down.
    """
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = _ISO_TS.sub("<ts>", text)
    text = _DURATION.sub("<dur>", text)
    for pattern in extra:
        try:
            text = re.sub(pattern, "<vol>", text)
        except re.error:
            continue
    lines = [line.rstrip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line.strip())


def signal_digest(text: str, extra: Iterable[str] = ()) -> str:
    return hashlib.sha256(normalize_signal(text, extra).encode("utf-8")).hexdigest()[:16]


def save_state(path: str, rows: Dict[str, VerifierResult], now: Optional[str] = None) -> None:
    """Write the baseline atomically — a half-written state file is worse than none."""
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    payload = {
        "schema": SCHEMA,
        "generated_at": now or _utc_now(),
        "rows": {name: row.to_dict() for name, row in rows.items()},
    }
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, path)


def load_state(path: Optional[str]) -> Optional[dict]:
    """Load a baseline. Any problem returns None: no baseline, never an exception."""
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict) or payload.get("schema") != SCHEMA:
        return None
    if not isinstance(payload.get("rows"), dict):
        return None
    return payload


def diff_results(
    previous: Optional[dict], current: Dict[str, VerifierResult]
) -> List[Transition]:
    """Transitions only. An identical run returns an empty list, by construction."""
    if not previous:
        return []
    old: Dict[str, dict] = previous.get("rows") or {}
    transitions: List[Transition] = []

    for name in sorted(current):
        now = current[name]
        if name not in old:
            transitions.append(Transition(name, "appeared", "-", now.status))
            continue
        before = VerifierResult.from_dict(old[name])
        if before.status != now.status:
            transitions.append(
                Transition(name, "status", before.status, now.status)
            )
        elif before.digest != now.digest:
            transitions.append(
                Transition(name, "signal", before.status, now.status)
            )

    for name in sorted(old):
        if name not in current:
            before = VerifierResult.from_dict(old[name])
            transitions.append(Transition(name, "vanished", before.status, "-"))

    return transitions


def _utc_now() -> str:
    import datetime

    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def summarise(results: Iterable[VerifierResult]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for res in results:
        counts[res.status] = counts.get(res.status, 0) + 1
    return counts
