"""Report rendering. Three shapes: human text, JSON rollup, revoke list.

Hard rule: no renderer may emit a credential value. Only paths, line numbers,
pattern ids, class names, signals and a 4-char fingerprint.
"""
import json
from typing import NamedTuple

from .classify import CLASSES

# One source of truth: the renderer must not be able to disagree with the
# classifier about what classes exist.
CLASS_ORDER = CLASSES


def class_rank(klass: str) -> int:
    """Lower is more specific. An unknown label sorts last, never first."""
    return CLASSES.index(klass) if klass in CLASSES else len(CLASSES)


class Finding(NamedTuple):
    path: str
    line: int
    pattern_id: str
    fingerprint: str
    value_len: int
    klass: str
    signals: tuple


class Report(NamedTuple):
    roots: list
    findings: list
    skipped: list
    files_scanned: int
    files_skipped: int

    # -- verdict ---------------------------------------------------------
    def is_unmeasurable(self) -> bool:
        """Zero files probed, or a root we could not open, proves nothing."""
        if self.files_scanned == 0:
            return True
        return any(str(reason).startswith("root-") for _, reason in self.skipped)

    def is_clean(self) -> bool:
        return not self.findings and not self.is_unmeasurable()

    def exit_code(self) -> int:
        if self.is_unmeasurable():
            return 2
        return 1 if self.findings else 0

    def counts_by_class(self) -> dict:
        counts: dict = {}
        for finding in self.findings:
            counts[finding.klass] = counts.get(finding.klass, 0) + 1
        return counts

    # -- renderers -------------------------------------------------------
    def as_text(self) -> str:
        counts = self.counts_by_class()
        lines = [
            "secretsurface: where key material actually lives",
            "roots: " + ", ".join(str(root) for root in self.roots),
            "files scanned: %d  skipped: %d" % (self.files_scanned, self.files_skipped),
        ]
        if self.is_unmeasurable():
            lines.append("verdict: UNMEASURABLE -- nothing was proven clean")
            for path, reason in self.skipped:
                if str(reason).startswith("root-"):
                    lines.append("  ! %s (%s)" % (path, reason))
        elif self.is_clean():
            lines.append("verdict: CLEAN -- no credential shapes outside expected stores")
        else:
            lines.append("verdict: %d findings in %d files" % (
                len(self.findings), len({f.path for f in self.findings})))
        if counts:
            lines.append("by class: " + "  ".join(
                "%s=%d" % (name, counts[name])
                for name in CLASS_ORDER if name in counts))
        if self.findings:
            lines.append("")
            for finding in self.findings:
                signals = ("  [" + ", ".join(finding.signals) + "]") if finding.signals else ""
                lines.append("%s:%d  %-18s %-11s fp=%s len=%d%s" % (
                    finding.path, finding.line, finding.pattern_id,
                    finding.klass, finding.fingerprint, finding.value_len, signals))
        lines.extend(self._skip_lines())
        return "\n".join(lines) + "\n"

    def _skip_lines(self) -> list:
        if not self.skipped:
            return []
        buckets: dict = {}
        for _, reason in self.skipped:
            key = str(reason).split(":")[0]
            buckets[key] = buckets.get(key, 0) + 1
        rendered = ", ".join("%s=%d" % (k, v) for k, v in sorted(buckets.items()))
        return ["", "skipped (not looked at, so not cleared): " + rendered,
                "  (full list in --json)"]

    def as_json(self) -> str:
        payload = {
            "tool": "secretsurface",
            "roots": [str(root) for root in self.roots],
            "files_scanned": self.files_scanned,
            "files_skipped": self.files_skipped,
            "verdict": ("unmeasurable" if self.is_unmeasurable()
                        else "clean" if not self.findings else "findings"),
            "summary": {
                "findings": len(self.findings),
                "files_with_findings": len({f.path for f in self.findings}),
                "by_class": self.counts_by_class(),
            },
            "findings": [
                {
                    "path": f.path,
                    "line": f.line,
                    "pattern_id": f.pattern_id,
                    "klass": f.klass,
                    "fingerprint": f.fingerprint,
                    "value_len": f.value_len,
                    "signals": list(f.signals),
                }
                for f in self.findings
            ],
            "skipped": [{"path": p, "reason": r} for p, r in self.skipped],
        }
        return json.dumps(payload, indent=2, sort_keys=False)

    def revoke_list(self) -> list:
        """Paths to rotate FROM. Never values, never line numbers."""
        return sorted({f.path for f in self.findings})
