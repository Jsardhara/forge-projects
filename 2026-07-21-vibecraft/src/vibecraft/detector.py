"""AST-based pattern detector for vibe-coding anti-patterns."""

import ast
import re
from pathlib import Path
from typing import Optional

from vibecraft.models import (
    CraftsmanshipReport,
    Finding,
    FindingCode,
    Severity,
)

# Patterns that indicate hardcoded values
_URL_PATTERN = re.compile(r"https?://[^\s\"']+", re.IGNORECASE)
_MAGIC_STRING_MIN_LEN = 8
_NESTING_THRESHOLD = 3
_FUNCTION_LINE_THRESHOLD = 50
_MAGIC_NUMBER_THRESHOLD = 3


class VibeDetector(ast.NodeVisitor):
    """AST visitor that collects vibe-coding anti-pattern findings."""

    def __init__(self, source: str, file_path: str):
        self.source = source
        self.lines = source.splitlines()
        self.file_path = file_path
        self.findings: list[Finding] = []
        self._nesting_depth = 0
        self._in_function = False
        self._in_class = False
        self._function_name = ""
        self._has_docstring = False
        self._current_function_lines = 0
        self._functions_defined = 0
        self._functions_with_doc = 0
        self._exception_handlers = 0
        self._proper_exception_handlers = 0
        self._named_constants: set[str] = set()
        self._names_used: set[str] = set()
        self._inconsistent_naming_found = False
        self._snake_names: set[str] = set()
        self._camel_names: set[str] = set()
        self._pascal_names: set[str] = set()
        self._magic_strings: set[str] = set()
        self._magic_numbers: set[int] = set()
        self._literal_lines: set[int] = set()
        self._collect_named_constants(source)

    def _collect_named_constants(self, source: str) -> None:
        """Pre-scan for UPPER_SNAKE_CASE names (likely constants) to filter magic values."""
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        name = t.id
                        if name.isupper() and "_" in name or name.isupper():
                            self._named_constants.add(name)
                    elif isinstance(t, ast.Attribute):
                        if isinstance(t.value, ast.Name) and t.attr.isupper():
                            self._named_constants.add(t.attr)

    def _is_magic(self, value: str) -> bool:
        if len(value) < _MAGIC_STRING_MIN_LEN:
            return False
        if value in self._named_constants:
            return False
        return True

    def _register_literal(self, node: ast.Constant) -> None:
        if isinstance(node.value, str) and self._is_magic(node.value):
            self._magic_strings.add(node.value)
            if hasattr(node, "lineno"):
                self._literal_lines.add(node.lineno)
        elif isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            if abs(node.value) not in (0, 1) and abs(node.value) < 10_000:
                self._magic_numbers.add(int(node.value))
                if hasattr(node, "lineno"):
                    self._literal_lines.add(node.lineno)

    def visit_Assign(self, node: ast.Assign) -> None:
        if self._in_function:
            if hasattr(node, "end_lineno") and node.end_lineno is not None:
                self._current_function_lines = max(self._current_function_lines, node.end_lineno)
            else:
                self._current_function_lines = max(self._current_function_lines, node.lineno)
        for t in node.targets:
            if isinstance(t, ast.Name):
                self._names_used.add(t.id)
                if self._is_snake(t.id):
                    self._snake_names.add(t.id)
                elif self._is_camel(t.id):
                    self._camel_names.add(t.id)
                elif self._is_pascal(t.id):
                    self._pascal_names.add(t.id)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        old_in_function = self._in_function
        old_function_name = self._function_name
        old_has_docstring = self._has_docstring
        old_nesting = self._nesting_depth

        self._in_function = True
        self._function_name = node.name
        self._has_docstring = bool(ast.get_docstring(node))
        self._nesting_depth = 0

        if self._is_snake(node.name):
            self._snake_names.add(node.name)
        elif self._is_camel(node.name):
            self._camel_names.add(node.name)
        elif self._is_pascal(node.name):
            self._pascal_names.add(node.name)

        if self._has_docstring:
            doc = (ast.get_docstring(node) or "").strip()
            if len(doc) < 5:
                self._add_finding(
                    FindingCode.EMPTY_DOCSTRING,
                    f"Function '{node.name}' has empty or trivial docstring",
                    Severity.WARNING,
                    node.lineno,
                )
        else:
            if not node.name.startswith("_"):
                self._add_finding(
                    FindingCode.MISSING_DOCSTRING,
                    f"Function '{node.name}' is missing a docstring",
                    Severity.INFO,
                    node.lineno,
                )

        self.generic_visit(node)

        # Use FunctionDef.end_lineno to get the actual last line of the function body
        func_end_lineno = getattr(node, "end_lineno", None) or node.lineno
        func_start_lineno = node.lineno
        func_total_lines = func_end_lineno - func_start_lineno + 1

        if func_total_lines > _FUNCTION_LINE_THRESHOLD:
            self._add_finding(
                FindingCode.LONG_FUNCTION,
                f"Function '{node.name}' is {func_total_lines} lines (threshold {_FUNCTION_LINE_THRESHOLD})",
                Severity.WARNING,
                node.lineno,
            )

        self._functions_defined += 1
        if self._has_docstring:
            self._functions_with_doc += 1

        self._in_function = old_in_function
        self._function_name = old_function_name
        self._has_docstring = old_has_docstring
        self._nesting_depth = old_nesting

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        if self._is_pascal(node.name):
            self._pascal_names.add(node.name)
        old_has_docstring = self._has_docstring
        self._has_docstring = bool(ast.get_docstring(node))
        if not self._has_docstring and not node.name.startswith("_"):
            self._add_finding(
                FindingCode.MISSING_DOCSTRING,
                f"Class '{node.name}' is missing a docstring",
                Severity.INFO,
                node.lineno,
            )
        self.generic_visit(node)
        self._has_docstring = old_has_docstring

    def visit_Try(self, node: ast.Try) -> None:
        self._exception_handlers += len(node.handlers)
        for handler in node.handlers:
            if handler.type is None:
                self._add_finding(
                    FindingCode.BARE_EXCEPT,
                    "Bare 'except:' clause catches all exceptions — be explicit",
                    Severity.WARNING,
                    handler.lineno,
                )
            elif isinstance(handler.type, ast.Name) and handler.type.id == "Exception":
                if handler.body and isinstance(handler.body[-1], ast.Pass):
                    self._add_finding(
                        FindingCode.EXCEPT_EXCEPTION_PASS,
                        f"'except Exception: pass' silently swallows errors in '{self._function_name or 'module'}'",
                        Severity.CRITICAL,
                        handler.lineno,
                    )
            if not handler.body or (len(handler.body) == 1 and isinstance(handler.body[0], ast.Pass)):
                self._add_finding(
                    FindingCode.EXCEPT_PASS,
                    "Empty or pass-only exception handler — errors are silently ignored",
                    Severity.WARNING,
                    handler.lineno,
                )
            self._proper_exception_handlers += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self._nesting_depth += 1
        if self._nesting_depth > _NESTING_THRESHOLD:
            self._add_finding(
                FindingCode.DEEP_NESTING,
                f"Control flow nesting depth {self._nesting_depth} exceeds threshold {_NESTING_THRESHOLD}",
                Severity.WARNING,
                node.lineno,
            )
        self.generic_visit(node)
        self._nesting_depth -= 1

    visit_AsyncFor = visit_For

    def visit_While(self, node: ast.While) -> None:
        self._nesting_depth += 1
        if self._nesting_depth > _NESTING_THRESHOLD:
            self._add_finding(
                FindingCode.DEEP_NESTING,
                f"Control flow nesting depth {self._nesting_depth} exceeds threshold {_NESTING_THRESHOLD}",
                Severity.WARNING,
                node.lineno,
            )
        self.generic_visit(node)
        self._nesting_depth -= 1

    def visit_If(self, node: ast.If) -> None:
        self._nesting_depth += 1
        if self._nesting_depth > _NESTING_THRESHOLD:
            self._add_finding(
                FindingCode.DEEP_NESTING,
                f"Control flow nesting depth {self._nesting_depth} exceeds threshold {_NESTING_THRESHOLD}",
                Severity.WARNING,
                node.lineno,
            )
        self.generic_visit(node)
        self._nesting_depth -= 1

    def visit_Expr(self, node: ast.Expr) -> None:
        if isinstance(node.value, ast.Constant):
            self._register_literal(node.value)
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        self._register_literal(node)
        self.generic_visit(node)

    def _add_finding(self, code: FindingCode, message: str, severity: Severity, line: int) -> None:
        self.findings.append(Finding(code=code, message=message, severity=severity, line=line))

    @staticmethod
    def _is_snake(name: str) -> bool:
        return "_" in name and name.islower()

    @staticmethod
    def _is_camel(name: str) -> bool:
        return name[0].islower() and any(c.isupper() for c in name) and "_" not in name

    @staticmethod
    def _is_pascal(name: str) -> bool:
        return name[0].isupper() and any(c.islower() for c in name)

    def _post_visit(self) -> None:
        """Run after visiting to check for line-level issues."""
        # Magic strings
        for line_no, line in enumerate(self.lines, 1):
            # Hardcoded URLs
            if _URL_PATTERN.search(line) and not self._in_import(line):
                self._add_finding(
                    FindingCode.HARDCODE_URL,
                    f"Hardcoded URL found: {_URL_PATTERN.search(line).group()[:60]}",
                    Severity.INFO,
                    line_no,
                )
            # Hardcoded paths (C:\ or / or ~/ patterns)
            if self._is_hardcoded_path(line):
                self._add_finding(
                    FindingCode.HARDCODE_PATH,
                    f"Hardcoded file path found",
                    Severity.INFO,
                    line_no,
                )
            # Print statements (likely debug leftovers)
            stripped = line.strip()
            if stripped.startswith("print(") and not stripped.startswith("print("):
                pass
            if stripped.startswith("print(") and "logger" not in stripped.lower():
                self._add_finding(
                    FindingCode.PRINT_IN_CODE,
                    "print() statement found — use logging instead in production code",
                    Severity.INFO,
                    line_no,
                )
            # Incomplete TODO
            if re.search(r"\bTODO\b", line) and not re.search(r"\bTODO\b.*\b\w{10,}\b", line):
                self._add_finding(
                    FindingCode.INCOMPLETE_TODO,
                    "TODO found without actionable description",
                    Severity.INFO,
                    line_no,
                )
            # Magic strings (in-line) — add finding regardless of _literal_lines
            for ms in self._magic_strings:
                if ms in line and len(ms) > _MAGIC_STRING_MIN_LEN:
                    self._add_finding(
                        FindingCode.MAGIC_STRING,
                        f"Magic string should be a named constant: {ms[:40]}",
                        Severity.INFO,
                        line_no,
                    )

        # Magic number findings
        for line_no, line in enumerate(self.lines, 1):
            for mn in self._magic_numbers:
                if str(mn) in line:
                    self._add_finding(
                        FindingCode.MAGIC_NUMBER,
                        f"Magic number {mn} should be a named constant",
                        Severity.INFO,
                        line_no,
                    )
                    break

        # Inconsistent naming
        naming_styles_used = sum(bool(s) for s in [self._snake_names, self._camel_names, self._pascal_names])
        if naming_styles_used >= 2 and (len(self._snake_names) + len(self._camel_names) + len(self._pascal_names)) >= 4:
            self._add_finding(
                FindingCode.INCONSISTENT_NAMING,
                f"Mixed naming conventions in same file: snake={len(self._snake_names)}, camel={len(self._camel_names)}, pascal={len(self._pascal_names)}",
                Severity.INFO,
                1,
            )

    @staticmethod
    def _is_hardcoded_path(line: str) -> bool:
        stripped = line.strip()
        if stripped.startswith(("#", "import", "from", "//", "/*", "*")):
            return False
        return bool(re.search(r"[\"'][A-Za-z]:[/\\]|[\"']/[^/\"']+|[\"']~[/\\]", line))

    @staticmethod
    def _in_import(line: str) -> bool:
        return any(kw in line for kw in ["import", "from", "href=", "src=", "url("])


def detect_patterns(source: str, file_path: str = "<unknown>") -> list[Finding]:
    """Detect vibe-coding anti-patterns in Python source code."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    detector = VibeDetector(source, file_path)
    detector.visit(tree)
    detector._post_visit()
    return detector.findings
