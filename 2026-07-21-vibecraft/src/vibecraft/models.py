"""Data models for vibecraft."""

from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class FindingCode(str, Enum):
    # Error handling
    BARE_EXCEPT = "bare_except"
    EXCEPT_PASS = "except_pass"
    EXCEPT_EXCEPTION_PASS = "except_exception_pass"
    # Documentation
    MISSING_DOCSTRING = "missing_docstring"
    EMPTY_DOCSTRING = "empty_docstring"
    # Complexity
    DEEP_NESTING = "deep_nesting"
    LONG_FUNCTION = "long_function"
    # Magic values
    MAGIC_STRING = "magic_string"
    MAGIC_NUMBER = "magic_number"
    # Quality
    HARDCODE_PATH = "hardcode_path"
    HARDCODE_URL = "hardcode_url"
    PRINT_IN_CODE = "print_in_code"
    INCOMPLETE_TODO = "incomplete_todo"
    EMPTY_BLOCK = "empty_block"
    # Naming
    INCONSISTENT_NAMING = "inconsistent_naming"


@dataclass(frozen=True)
class Finding:
    code: FindingCode
    message: str
    severity: Severity
    line: int
    column: int = 0

    def to_dict(self) -> dict:
        return {
            "code": self.code.value,
            "message": self.message,
            "severity": self.severity.value,
            "line": self.line,
            "column": self.column,
        }


@dataclass
class CraftsmanshipReport:
    file_path: str
    score: float  # 0-100
    grade: str  # A/B/C/D/F
    total_lines: int
    finding_count: int
    findings: list[Finding] = field(default_factory=list)
    doc_coverage: float = 0.0  # 0.0-1.0
    error_handling_score: float = 0.0  # 0.0-1.0
    complexity_score: float = 0.0  # 0.0-1.0
    naming_score: float = 0.0  # 0.0-1.0

    def band(self) -> str:
        if self.score >= 90:
            return "excellent"
        elif self.score >= 70:
            return "good"
        elif self.score >= 50:
            return "fair"
        else:
            return "poor"

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "score": round(self.score, 1),
            "grade": self.grade,
            "band": self.band(),
            "total_lines": self.total_lines,
            "finding_count": self.finding_count,
            "findings": [f.to_dict() for f in self.findings],
            "doc_coverage": round(self.doc_coverage, 3),
            "error_handling_score": round(self.error_handling_score, 3),
            "complexity_score": round(self.complexity_score, 3),
            "naming_score": round(self.naming_score, 3),
        }
