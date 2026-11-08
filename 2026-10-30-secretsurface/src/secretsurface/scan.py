"""Scan orchestration: walk -> match -> classify -> blast radius -> report."""
from pathlib import Path

from .blast import blast_signals, publication_rank
from .classify import classify_path
from .patterns import find_matches
from .report import Finding, Report, class_rank
from .walk import DEFAULT_MAX_BYTES, read_text, scan_tree

__all__ = ["Finding", "Report", "scan"]


def scan(roots, max_bytes: int = DEFAULT_MAX_BYTES) -> Report:
    """Scan roots for credential shapes and classify every sighting."""
    root_list = [Path(root) for root in roots]
    files, skipped = scan_tree(root_list, max_bytes=max_bytes)
    findings: list = []

    for path in files:
        text = read_text(path)
        if text is None:
            skipped.append((str(path), "unreadable: read failed"))
            continue
        matches = find_matches(text)
        if not matches:
            continue
        klass = classify_path(str(path))
        signals = blast_signals(path, klass)
        for match in matches:
            findings.append(Finding(
                path=str(path),
                line=match.line,
                pattern_id=match.pattern_id,
                fingerprint=match.fingerprint,
                value_len=match.value_len,
                klass=klass,
                signals=signals,
            ))

    findings.sort(key=_exposure_key)
    findings = _mark_live_duplicates(findings)
    skipped.sort(key=lambda pair: pair[0])
    return Report(
        roots=[str(root) for root in root_list],
        findings=findings,
        skipped=skipped,
        files_scanned=len(files),
        files_skipped=len(skipped),
    )


def _exposure_key(finding):
    """Rank by whether the file leaves the machine, then by store class.

    Published-ness is the question that decides whether someone rotates a key
    today; store class only breaks ties. A committed agent config with a live key
    outranks a superseded backup that git has never seen, which is the ordering
    the measured data supports (1,122 of 104,185 public `.claude/settings.local.json`
    files carry a real secret).
    """
    return (
        publication_rank(finding.signals),
        class_rank(finding.klass),
        finding.path,
        finding.line,
        finding.pattern_id,
    )


_BACKUP_CLASSES = ("env-backup", "backup-blob")


def _mark_live_duplicates(findings):
    """Flag a backup that still holds the value the live .env holds.

    A key in a backup is mild. A backup whose fingerprint matches the LIVE
    value means rotating .env alone leaves a working copy of the same key on
    disk -- which is how a finished-looking rotation stays unfinished.
    """
    live = {f.fingerprint for f in findings if f.klass == "env"}
    if not live:
        return findings
    marked: list = []
    for finding in findings:
        if finding.klass in _BACKUP_CLASSES and finding.fingerprint in live:
            finding = finding._replace(
                signals=finding.signals + ("duplicate-of-live-env",))
        marked.append(finding)
    return marked
