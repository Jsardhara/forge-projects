"""Report assembly for tokenaudit.

Combines parsing, pricing, profiling, and the recommendation engine into a single
CostReport. This is the main entry point used by the CLI.
"""
from __future__ import annotations

from typing import Dict, Optional

from .audit import recommendations
from .models import CostReport, Session
from .pricing import DEFAULT_PRICING, cost_for
from .profile import file_reads, phase_breakdown, waste_findings


def build_report(session: Session,
                 pricing_table: Optional[Dict] = None) -> CostReport:
    table = pricing_table or DEFAULT_PRICING
    total_input = sum(m.usage.input_tokens for m in session.messages)
    total_output = sum(m.usage.output_tokens for m in session.messages)
    by_model: Dict[str, float] = {}
    total_cost = 0.0
    for m in session.messages:
        c = cost_for(m.model, m.usage.input_tokens, m.usage.output_tokens, table)
        total_cost += c
        key = m.model or "unknown"
        by_model[key] = by_model.get(key, 0.0) + c

    report = CostReport(
        session=session.source,
        agent=session.agent,
        total_input=total_input,
        total_output=total_output,
        total_cost=total_cost,
        by_model=by_model,
        phase=phase_breakdown(session),
        file_reads=file_reads(session),
        findings=waste_findings(session, table),
    )
    report.recommendations = recommendations(report)
    return report
