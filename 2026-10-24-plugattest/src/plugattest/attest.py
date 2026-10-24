"""Compare claimed capabilities against detected capabilities. Fail closed."""

import os

from .manifest import KNOWN_CAPABILITIES, load_declared
from .models import Finding, Report, Severity
from .scanner import scan_package

EXIT_CLEAN = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2


def _finding(code, severity, location, message, capability=""):
    return Finding(code=code, severity=severity, location=location,
                   message=message, capability=capability)


def _declaration_findings(declared, detected):
    """Latest-risk findings about the capability claim itself."""
    findings = []
    if not declared.sources:
        for capability in detected:
            findings.append(_finding(
                "PA-005", Severity.FLAG, "<no manifest>",
                "no manifest found yet the package uses this capability",
                capability))
    elif not declared.declares_capabilities and detected:
        for capability in detected:
            findings.append(_finding(
                "PA-003", Severity.WARN, ",".join(declared.sources),
                "manifest makes no capability claim while the code uses this capability",
                capability))

    for capability in declared.unknown:
        findings.append(_finding(
            "PA-006", Severity.WARN, ",".join(declared.sources) or "<manifest>",
            "declared capability is not a known capability token and cannot be attested",
            capability))

    for error in declared.errors:
        findings.append(_finding(
            "PA-007", Severity.WARN, "<manifest>",
            "manifest could not be parsed: %s" % error))
    return findings


def _diff_findings(declared_set, detected_hits):
    """Undeclared capability use (FLAG) vs declared-but-unused (INFO)."""
    findings = []
    detected_caps = sorted({hit.capability for hit in detected_hits})
    for capability in detected_caps:
        if capability not in declared_set:
            hit = next(h for h in detected_hits if h.capability == capability)
            findings.append(_finding(
                "PA-001", Severity.FLAG, "%s:%d" % (hit.path, hit.line),
                "capability used but never declared (signal: %s)" % hit.signal,
                capability))
    for capability in sorted(declared_set - set(detected_caps)):
        if capability in KNOWN_CAPABILITIES:
            findings.append(_finding(
                "PA-002", Severity.INFO, ",".join(declared_set) or "<manifest>",
                "capability declared but no use detected in the package source",
                capability))
    return findings


def _hook_findings(declared):
    findings = []
    for hook in declared.hooks:
        if "auto_hook" not in declared.capabilities:
            findings.append(_finding(
                "PA-004", Severity.FLAG, ",".join(declared.sources),
                "auto-execution hook '%s' runs on install but auto_hook is not declared"
                % hook, "auto_hook"))
    return findings


def attest(root):
    """Attest one package directory. Raises OSError when the path is not a directory."""
    if not os.path.isdir(root):
        raise OSError("package directory not found: %s" % root)

    declared = load_declared(root)
    hits = scan_package(root)
    declared_set = set(declared.capabilities)

    findings = []
    findings.extend(_declaration_findings(declared, sorted({h.capability for h in hits})))
    # A "use without declaration" finding is only meaningful when the package
    # actually made a capability claim. Without one, PA-003/PA-005 already says so.
    if declared.declares_capabilities:
        findings.extend(_diff_findings(declared_set, hits))
    findings.extend(_hook_findings(declared))

    return Report(
        package=os.path.basename(os.path.abspath(root)),
        declared=declared.capabilities,
        detected=tuple(sorted({h.capability for h in hits})),
        findings=tuple(findings),
    )
