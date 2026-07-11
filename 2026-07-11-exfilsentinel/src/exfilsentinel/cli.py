from __future__ import annotations

import argparse
import json
import random
import string
import sys
from datetime import datetime, timezone

from .detector import DetectionEngine
from .models import ApiEvent, RiskClass
from .watermark import ProvenanceRecord, detect, embed, verify


def _gen_nonce(n: int = 12) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def _load_events(path: str) -> list[ApiEvent]:
    with open(path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    events: list[ApiEvent] = []
    for d in raw:
        ts = datetime.fromisoformat(d["timestamp"])
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        events.append(
            ApiEvent(
                actor_id=d["actor_id"],
                model=d["model"],
                timestamp=ts,
                prompt_tokens=int(d.get("prompt_tokens", 0)),
                completion_tokens=int(d.get("completion_tokens", 0)),
                endpoint=d.get("endpoint", "/v1/chat/completions"),
                ip=d.get("ip", ""),
                prompt_template_hash=d.get("prompt_template_hash", ""),
            )
        )
    return events


def _read_text(args) -> str:
    if getattr(args, "text", None):
        return args.text
    with open(args.text_file, "r", encoding="utf-8") as fh:
        return fh.read()


def cmd_scan(args) -> int:
    events = _load_events(args.events)
    engine = DetectionEngine()
    off = None
    if args.offboarding:
        off = datetime.fromisoformat(args.offboarding)
        if off.tzinfo is None:
            off = off.replace(tzinfo=timezone.utc)
    verdict = engine.evaluate(
        args.actor, events, offboarding_since=off, allowlisted=args.allowlisted
    )
    print(f"Actor: {verdict.actor_id}")
    print(f"Risk score: {verdict.risk_score:.4f}")
    print(f"Classification: {verdict.risk_class.value.upper()}")
    for ev in verdict.evidence:
        print(ev)
    # CI gate: non-zero exit on confirmed exfiltration.
    return 1 if verdict.risk_class == RiskClass.EXFILTRATION else 0


def cmd_embed(args) -> int:
    record = ProvenanceRecord(
        org_id=args.org,
        model=args.model,
        issued_at=datetime.now(timezone.utc),
        nonce=args.nonce or _gen_nonce(),
    )
    wm = embed(args.text, record)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(wm.text)
        print(f"wrote watermarked text to {args.out}")
    else:
        sys.stdout.write(wm.text + "\n")
    return 0


def cmd_verify(args) -> int:
    text = _read_text(args)
    rec = verify(text)
    if rec is None:
        print("NO PROVENANCE RECORD FOUND")
        return 1
    print(f"org_id: {rec.org_id}")
    print(f"model: {rec.model}")
    print(f"issued_at: {rec.issued_at.isoformat()}")
    print(f"nonce: {rec.nonce}")
    return 0


def cmd_detect(args) -> int:
    text = _read_text(args)
    return 0 if detect(text) else 1


def _add_text_args(p: argparse.ArgumentParser) -> None:
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--text", help="text to inspect")
    g.add_argument("--text-file", help="file containing text to inspect")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="exfilsentinel",
        description="AI model-access exfiltration detector + output-provenance watermarking",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("scan", help="score an actor's API access for exfiltration")
    sp.add_argument("--events", required=True, help="JSON file of ApiEvent records")
    sp.add_argument("--actor", required=True, help="actor_id to evaluate")
    sp.add_argument("--offboarding", default=None, help="ISO timestamp of offboarding")
    sp.add_argument("--allowlisted", action="store_true", help="treat actor as sanctioned")
    sp.set_defaults(func=cmd_scan)

    ep = sub.add_parser("embed", help="embed a provenance watermark into text")
    ep.add_argument("--text", required=True)
    ep.add_argument("--org", required=True)
    ep.add_argument("--model", required=True)
    ep.add_argument("--nonce", default=None)
    ep.add_argument("--out", default=None)
    ep.set_defaults(func=cmd_embed)

    vp = sub.add_parser("verify", help="verify/extract a provenance watermark")
    _add_text_args(vp)
    vp.set_defaults(func=cmd_verify)

    dp = sub.add_parser("detect", help="detect presence of a watermark")
    _add_text_args(dp)
    dp.set_defaults(func=cmd_detect)

    args = p.parse_args(argv)
    return args.func(args)


__all__ = ["main"]
