"""Craftsmanship scoring for vibecraft."""

import math
from dataclasses import dataclass

from vibecraft.detector import VibeDetector
from vibecraft.models import CraftsmanshipReport, FindingCode, Severity


@dataclass
class ScoreResult:
    score: float
    grade: str
    doc_coverage: float
    error_handling_score: float
    complexity_score: float
    naming_score: float


def score_craftsmanship(source: str, file_path: str) -> CraftsmanshipReport:
    """Analyze Python source and return a craftsmanship report."""
    lines = source.splitlines()
    total_lines = len(lines)

    if total_lines == 0:
        return CraftsmanshipReport(
            file_path=file_path,
            score=100.0,
            grade="A",
            total_lines=0,
            finding_count=0,
            doc_coverage=1.0,
            error_handling_score=1.0,
            complexity_score=1.0,
            naming_score=1.0,
        )

    # Run AST detector
    tree = __import__("ast").parse(source)
    detector = VibeDetector(source, file_path)
    detector.visit(tree)
    detector._post_visit()
    findings = detector.findings

    # --- Subscores ---
    # 1. Documentation coverage
    functions_defined = max(detector._functions_defined, 1)
    doc_coverage = detector._functions_with_doc / functions_defined

    # 2. Error handling score
    exception_ratio = 0.0
    if len(findings) > 0:
        error_findings = sum(
            1 for f in findings
            if f.code in (FindingCode.BARE_EXCEPT, FindingCode.EXCEPT_PASS,
                          FindingCode.EXCEPT_EXCEPTION_PASS)
        )
        exception_ratio = min(error_findings / max(len(findings), 1) * 4, 1.0)
    error_handling_score = 1.0 - exception_ratio

    # 3. Complexity score (based on nesting + long function findings)
    complexity_penalties = 0.0
    nesting_findings = sum(1 for f in findings if f.code == FindingCode.DEEP_NESTING)
    long_fn_findings = sum(1 for f in findings if f.code == FindingCode.LONG_FUNCTION)
    complexity_penalties = min((nesting_findings * 0.15 + long_fn_findings * 0.2), 0.8)
    complexity_score = 1.0 - complexity_penalties

    # 4. Naming consistency score
    naming_styles = [detector._snake_names, detector._camel_names, detector._pascal_names]
    used_styles = sum(1 for s in naming_styles if len(s) > 0)
    if used_styles >= 2 and (len(detector._snake_names) + len(detector._camel_names) + len(detector._pascal_names)) >= 4:
        naming_score = 0.6
    else:
        naming_score = 1.0

    # 5. Magic value penalty
    magic_count = len(detector._magic_strings) + len(detector._magic_numbers)
    magic_penalty = min(magic_count * 0.05, 0.4)

    # --- Overall score ---
    critical_penalties = sum(0.15 for f in findings if f.severity == Severity.CRITICAL)
    warning_penalties = sum(0.05 for f in findings if f.severity == Severity.WARNING)
    info_penalties = sum(0.01 for f in findings if f.severity == Severity.INFO)

    magic_score = 1.0 - magic_penalty
    base_score = (
        doc_coverage * 20
        + error_handling_score * 25
        + complexity_score * 25
        + naming_score * 15
        + magic_score * 15
    )
    score = base_score - critical_penalties - warning_penalties - info_penalties
    score = max(0.0, min(100.0, score))

    # Grade
    grade = _score_to_grade(score)

    return CraftsmanshipReport(
        file_path=file_path,
        score=score,
        grade=grade,
        total_lines=total_lines,
        finding_count=len(findings),
        findings=findings,
        doc_coverage=doc_coverage,
        error_handling_score=error_handling_score,
        complexity_score=complexity_score,
        naming_score=naming_score,
    )


def _score_to_grade(score: float) -> str:
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 50:
        return "D"
    else:
        return "F"
