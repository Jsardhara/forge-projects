"""Rule file loading and evaluation.

A rule file is data, not code: an advisory identity plus one entry per affected
product. Two evaluation kinds exist because the advisory itself has two shapes:

* ``range``      -- a package with a version span and a set of published fixes
                    (Python wheels, system libraries). The ``fixed`` list wins
                    inside the span, because releases like 1.1.1 sit numerically
                    inside "1.0.3 - 1.2.0" while being a fix, not a victim.
* ``runtime_lines`` -- a runtime with per-major support lines (Node.js), where a
                    line not named in the file is end-of-life and has no fix at
                    all, and an unlisted *newer* line cannot be attested.

The evaluator never guesses: anything it cannot place returns ``unknown``.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

from .version import VersionError, base, compare

__all__ = [
    "RuleError",
    "Evaluation",
    "RuleSet",
    "default_rules_path",
    "PRODUCTS_KEY",
]

PRODUCTS_KEY = "products"
STATUS_AFFECTED = "affected"
STATUS_PATCHED = "patched"
STATUS_NOT_AFFECTED = "not_affected"
STATUS_NOT_LISTED = "not_listed"
STATUS_UNKNOWN = "unknown"


class RuleError(ValueError):
    """A rule file is missing, unreadable, or malformed."""


@dataclass(frozen=True)
class Evaluation:
    status: str
    product_id: Optional[str] = None
    reason: str = ""
    fix_hint: Optional[str] = None
    note: str = ""


@dataclass(frozen=True)
class Product:
    id: str
    ecosystem: str
    package: str
    kind: str
    raw: Dict

    @property
    def packages(self) -> List[str]:
        declared = self.raw.get("packages")
        if declared:
            return [str(name) for name in declared]
        return [self.package]

    @property
    def note(self) -> str:
        return str(self.raw.get("note", ""))


def default_rules_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "brotli-decoder.json")


class RuleSet:
    def __init__(self, document: Dict):
        self._document = document
        self.advisory: Dict = document.get("advisory", {})
        self.products: List[Product] = [_product(entry) for entry in _product_entries(document)]

    @classmethod
    def load(cls, path: str) -> "RuleSet":
        try:
            with open(path, "r", encoding="utf-8") as handle:
                document = json.load(handle)
        except FileNotFoundError as exc:
            raise RuleError("rule file not found: %s" % path) from exc
        except OSError as exc:
            raise RuleError("rule file unreadable: %s (%s)" % (path, exc)) from exc
        except json.JSONDecodeError as exc:
            raise RuleError("rule file is not valid JSON: %s (%s)" % (path, exc)) from exc
        if not isinstance(document, dict):
            raise RuleError("rule file must contain a JSON object: %s" % path)
        return cls(document)

    def find(self, ecosystem: str, package: str) -> Optional[Product]:
        wanted = package.strip().lower()
        for product in self.products:
            if product.ecosystem != ecosystem:
                continue
            if wanted in [name.lower() for name in product.packages]:
                return product
        return None

    def evaluate(self, ecosystem: str, package: str, version: Optional[str]) -> Evaluation:
        product = self.find(ecosystem, package)
        if product is None:
            return Evaluation(STATUS_NOT_LISTED, None, "no rule for this package")
        if not version:
            return Evaluation(
                STATUS_UNKNOWN, product.id, "version could not be determined", note=product.note
            )
        try:
            if product.kind == "range":
                return _eval_range(product, version)
            if product.kind == "runtime_lines":
                return _eval_runtime_lines(product, version)
        except VersionError as exc:
            return Evaluation(
                STATUS_UNKNOWN, product.id, "unparsable version %r: %s" % (version, exc)
            )
        raise RuleError("product %s has unsupported kind %r" % (product.id, product.kind))


def _product_entries(document: Dict) -> List[Dict]:
    entries = document.get(PRODUCTS_KEY)
    if not isinstance(entries, list) or not entries:
        raise RuleError("rule file has no '%s' list" % PRODUCTS_KEY)
    return entries


def _product(entry: Dict) -> Product:
    for field in ("id", "ecosystem", "package", "kind"):
        if not entry.get(field):
            raise RuleError("product entry missing %r: %r" % (field, entry))
    if entry["kind"] not in ("range", "runtime_lines"):
        raise RuleError("unsupported product kind %r" % (entry["kind"],))
    return Product(
        id=str(entry["id"]),
        ecosystem=str(entry["ecosystem"]),
        package=str(entry["package"]),
        kind=str(entry["kind"]),
        raw=entry,
    )


def _eval_range(product: Product, version: str) -> Evaluation:
    spans = product.raw.get("affected") or []
    fixed = [str(item) for item in product.raw.get("fixed") or []]
    fix_hint = ", ".join(fixed) if fixed else None

    if any(_same(version, item) for item in fixed):
        return Evaluation(
            STATUS_PATCHED, product.id, "matches a published fixed version", fix_hint, product.note
        )

    core = base(version)
    for span in spans:
        if _in_span(core, span):
            return Evaluation(
                STATUS_AFFECTED,
                product.id,
                "inside the affected span %s" % _describe_span(span),
                fix_hint,
                product.note,
            )
    return Evaluation(
        STATUS_NOT_AFFECTED, product.id, "outside the affected span", fix_hint, product.note
    )


def _eval_runtime_lines(product: Product, version: str) -> Evaluation:
    lines: Dict[str, str] = {
        str(key): str(value) for key, value in (product.raw.get("lines") or {}).items()
    }
    major = base(version)[0]
    known_majors = sorted(int(key) for key in lines)

    if str(major) in lines:
        fix = lines[str(major)]
        if compare(version, fix) < 0:
            return Evaluation(
                STATUS_AFFECTED,
                product.id,
                "line %d is affected below %s" % (major, fix),
                fix,
                product.note,
            )
        return Evaluation(
            STATUS_PATCHED, product.id, "line %d is at or above %s" % (major, fix), fix, product.note
        )

    if known_majors and major < max(known_majors):
        return Evaluation(
            STATUS_AFFECTED,
            product.id,
            "line %d is end-of-life for this advisory and has no fix" % major,
            None,
            product.note or str(product.raw.get("eol_note", "")),
        )

    return Evaluation(
        STATUS_UNKNOWN,
        product.id,
        "line %d is not covered by this rule file; cannot attest" % major,
        None,
        product.note,
    )


def _same(left: str, right: str) -> bool:
    try:
        return compare(left, right) == 0
    except VersionError:
        return False


def _in_span(core, span: Dict) -> bool:
    low = span.get("min")
    high = span.get("max")
    high_exclusive = span.get("max_exclusive")
    if low is not None and tuple(core) < base(str(low)):
        return False
    if high is not None and tuple(core) > base(str(high)):
        return False
    if high_exclusive is not None and tuple(core) >= base(str(high_exclusive)):
        return False
    return True


def _describe_span(span: Dict) -> str:
    low = span.get("min", "")
    high = span.get("max")
    exclusive = span.get("max_exclusive")
    if high is not None:
        return "%s - %s" % (low, high)
    if exclusive is not None:
        return "%s - below %s" % (low, exclusive)
    return ">= %s" % low
