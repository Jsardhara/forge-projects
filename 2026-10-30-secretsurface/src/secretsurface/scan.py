"""Scan orchestration: walk -> match -> classify -> blast radius -> report."""
from pathlib import Path

from .blast import blast_signals
from .classify import classify_path
from .patterns import find_matches
from .report import Finding, Report
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

    findings.sort(key=lambda f: (f.path, f.line, f.pattern_id))
    findings = _mark_live_duplicates(findings)
    skipped.sort(key=lambda pair: pair[0])
    return Report(
        roots=[str(root) for root in root_list],
        findings=findings,
        skipped=skipped,
        files_scanned=len(files),
        files_skipped=len(skipped),
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
