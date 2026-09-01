"""feescope -- ad-spend surcharge & fee-opaqueness audit engine.

Deterministic, offline, zero-dependency. Mirrors the FTC v Amazon 'secret ad
surcharge' compliance vector: reconcile billed line items against a trusted
'verified' spend, flag opaque/stacked fee buckets, and watch the aggregate
fee-to-billed ratio and overall reconciliation.

Verdict is SEVERITY-DOMINANT (worst single finding), by design -- see memguard
lesson. `score` is only the weighted magnitude used by the CLI gate threshold.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .models import (
    SEVERITY_RANK,
    SEVERITY_SCORE,
    VERDICT_FROM_RANK,
    FeeItem,
    Finding,
    InvoiceReport,
    Severity,
)


@dataclass
class ScanConfig:
    tolerance: float = 0.005      # relative allowed drift (0.5%)
    flag_tolerance: float = 0.05  # reconciliation mismatch beyond this => FLAG
    max_fee_ratio: float = 0.20   # aggregate fees / billed beyond this => WARN


OPAQUE_STOPWORDS = frozenset(
    {
        "a", "an", "the", "and", "fee", "fees", "for", "of", "to", "charge",
        "charges", "platform", "service", "services", "servicing", "admin",
        "administrative", "administration", "processing", "process", "misc",
        "miscellaneous", "other", "handling", "management", "access", "tech",
        "technology", "setup", "set-up", "maintenance", "operational",
    }
)


class FeeScopeScanner:
    def __init__(self, config: Optional[ScanConfig] = None) -> None:
        self._cfg = config or ScanConfig()

    def scan(
        self,
        items: List[FeeItem],
        invoice_id: str = "invoice",
        expected_total: Optional[float] = None,
    ) -> InvoiceReport:
        findings: List[Finding] = []

        total_billed = sum((i.amount or 0.0) for i in items)
        fee_items = [i for i in items if i.category == "fee"]
        total_fees = sum((i.amount or 0.0) for i in fee_items)
        fee_ratio = (total_fees / total_billed) if total_billed else 0.0

        # FEE-001  opaque / unexplained fee line (no transparent subcategory)
        for item in fee_items:
            desc = item.description or ""
            words = [w for w in desc.lower().split() if w]
            opaque = (not words) or all(w in OPAQUE_STOPWORDS for w in words)
            if item.category == "other":
                opaque = True
            if opaque:
                findings.append(
                    Finding(
                        "FEE-001",
                        Severity.WARN,
                        f"Opaque fee line '{item.line_id}': '{desc or '<no description>'}' "
                        f"has no transparent subcategory",
                        item.line_id,
                    )
                )

        # FEE-002  hidden surcharge: billed > independently-verified spend
        for item in items:
            v = item.verified
            if v is not None and abs(v) > 1e-9 and item.amount is not None:
                delta = item.amount - v
                if delta > self._cfg.tolerance * abs(v):
                    findings.append(
                        Finding(
                            "FEE-002",
                            Severity.FLAG,
                            f"Hidden surcharge on '{item.line_id}': billed ${item.amount:.2f} "
                            f"> verified ${v:.2f} (delta ${delta:.2f}, +{delta / abs(v) * 100:.2f}%)",
                            item.line_id,
                        )
                    )

        # FEE-003  fee-stacking: multiple fee lines on one base purchase
        buckets: Dict[str, int] = {}
        for item in fee_items:
            if item.attached_to:
                buckets[item.attached_to] = buckets.get(item.attached_to, 0) + 1
        for base in sorted(buckets):
            count = buckets[base]
            if count > 1:
                findings.append(
                    Finding(
                        "FEE-003",
                        Severity.WARN,
                        f"Fee-stacking: {count} fee lines attach to base purchase "
                        f"'{base}' (double-count risk)",
                        None,
                    )
                )

        # FEE-004  aggregate fee-to-billed ratio exceeds cap (disclosure pattern)
        if total_billed > 0 and fee_ratio > self._cfg.max_fee_ratio:
            findings.append(
                Finding(
                    "FEE-004",
                    Severity.WARN,
                    f"Aggregate fees {fee_ratio * 100:.1f}% of billed exceed cap "
                    f"{self._cfg.max_fee_ratio * 100:.1f}%",
                    None,
                )
            )

        # FEE-005  overall reconciliation: sum(line items) vs expected total
        if expected_total is not None:
            denom = max(abs(expected_total), abs(total_billed), 1e-9)
            diff = abs(total_billed - expected_total) / denom
            if diff > self._cfg.flag_tolerance:
                findings.append(
                    Finding(
                        "FEE-005",
                        Severity.FLAG,
                        f"Reconciliation mismatch: billed ${total_billed:.2f} vs "
                        f"expected ${expected_total:.2f} ({diff * 100:.2f}%)",
                        None,
                    )
                )
            elif diff > self._cfg.tolerance:
                findings.append(
                    Finding(
                        "FEE-005",
                        Severity.WARN,
                        f"Reconciliation drift: billed ${total_billed:.2f} vs "
                        f"expected ${expected_total:.2f} ({diff * 100:.2f}%)",
                        None,
                    )
                )

        # severity-dominant verdict; score only as weighted magnitude
        if findings:
            worst = max((f.severity for f in findings), key=lambda s: SEVERITY_RANK[s])
            verdict = VERDICT_FROM_RANK[SEVERITY_RANK[worst]]
        else:
            worst, verdict = Severity.PASS, VERDICT_FROM_RANK[0]
        score = min(100.0, sum(SEVERITY_SCORE[f.severity] for f in findings))

        return InvoiceReport(
            invoice_id=invoice_id,
            verdict=verdict,
            score=score,
            findings=findings,
            total_billed=total_billed,
            total_fees=total_fees,
            fee_ratio=fee_ratio,
        )