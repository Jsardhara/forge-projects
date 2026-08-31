"""Aggregation and evaluation engine for capalarm."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from capalarm.models import (
    BreachForecast,
    Finding,
    PlanUsage,
    Severity,
    UsageSample,
)

# Number of days of "today" margin to treat a breaching project as imminent.
_DAYS_WARN_HORIZON = 3.0


def aggregate(
    samples: list[UsageSample],
) -> dict[str, PlanUsage]:
    """Collapse a list of UsageSample into per-provider aggregates.

    Computes total tokens, observation window (as seeded by sample timestamps),
    and peak tokens-per-minute (derived from any pair of consecutive samples
    within the same 60-second bucket).
    """
    by_provider: dict[str, PlanUsage] = {}
    # Bucket samples per provider into 1-minute windows to estimate peak rate.
    rate_buckets: dict[tuple[str, datetime], int] = {}

    for s in sorted(samples, key=lambda x: (x.provider, x.timestamp)):
        agg = by_provider.setdefault(s.provider, PlanUsage(provider=s.provider))
        agg.total_tokens += s.tokens
        if agg.window_start is None or s.timestamp < agg.window_start:
            agg.window_start = s.timestamp
        if agg.window_end is None or s.timestamp > agg.window_end:
            agg.window_end = s.timestamp

        minute_key = s.timestamp.replace(second=0, microsecond=0)
        bucket = rate_buckets.get((s.provider, minute_key), 0) + s.tokens
        rate_buckets[(s.provider, minute_key)] = bucket
        if bucket > agg.peak_tokens_per_min:
            agg.peak_tokens_per_min = bucket

    return by_provider


def max_finding_severity(findings: list[Finding]) -> str:
    return Severity.worst(*(f.severity for f in findings))


def evaluate(
    provider: str,
    usage: PlanUsage,
    plan,
) -> tuple[list[Finding], BreachForecast]:
    """Assess one provider's aggregate against its plan.

    Returns (findings, forecast). Cap utilisation, soft/hard-cap crossings and
    rate-limit tier checks produce findings; the forecast projects days-to-cap
    assuming a linear burn rate extrapolated from the observed window.
    """
    findings: list[Finding] = []

    if plan is None:
        findings.append(
            Finding(
                rule="CAPL-000",
                severity=Severity.CRIT,
                message=f"{provider}: no matching plan configured for evaluation",
            )
        )
        return findings, BreachForecast(provider=provider)

    if usage.total_tokens <= 0:
        findings.append(
            Finding(
                rule="CAPL-001",
                severity=Severity.PASS,
                message=f"{provider}: no usage in window",
            )
        )
        return findings, BreachForecast(provider=provider)

    hard_cap = plan.hard_cap
    soft_cap = plan.effective_soft_cap()

    # -- cap utilisation -----------------------------------------------------
    pct = usage.total_tokens / hard_cap
    if usage.total_tokens >= hard_cap:
        findings.append(
            Finding(
                rule="CAPL-002",
                severity=Severity.CRIT,
                message=(
                    f"{provider}: hard cap EXCEEDED "
                    f"({usage.total_tokens:,}/{hard_cap:,} tokens, {pct:.0%})"
                ),
            )
        )
    elif usage.total_tokens >= soft_cap:
        findings.append(
            Finding(
                rule="CAPL-003",
                severity=Severity.WARN,
                message=(
                    f"{provider}: at/over soft cap "
                    f"({usage.total_tokens:,}/{hard_cap:,} tokens, {pct:.0%})"
                ),
            )
        )
    else:
        findings.append(
            Finding(
                rule="CAPL-004",
                severity=Severity.PASS,
                message=(
                    f"{provider}: {pct:.0%} of hard cap "
                    f"({usage.total_tokens:,}/{hard_cap:,} tokens)"
                ),
            )
        )

    # -- rate-limit tier -----------------------------------------------------
    if plan.rate_limit is not None and usage.peak_tokens_per_min > plan.rate_limit:
        findings.append(
            Finding(
                rule="CAPL-005",
                severity=Severity.WARN,
                message=(
                    f"{provider}: rate tier exceeded "
                    f"({usage.peak_tokens_per_min:,} t/m > {plan.rate_limit:,} t/m)"
                ),
            )
        )
    elif plan.rate_limit is not None:
        findings.append(
            Finding(
                rule="CAPL-006",
                severity=Severity.PASS,
                message=(
                    f"{provider}: {usage.peak_tokens_per_min:,} t/m peak "
                    f"<= {plan.rate_limit:,} t/m rate tier"
                ),
            )
        )

    # -- days-to-breach forecast --------------------------------------------
    forecast = _forecast(provider, usage, hard_cap)
    if forecast.days_to_cap is not None and forecast.days_to_cap < _DAYS_WARN_HORIZON:
        findings.append(
            Finding(
                rule="CAPL-007",
                severity=Severity.WARN,
                message=(
                    f"{provider}: on pace to breach hard cap in "
                    f"{forecast.days_to_cap:.1f}d (burn {forecast.daily_burn:,.0f} t/day)"
                ),
            )
        )

    return findings, forecast


def _forecast(
    provider: str, usage: PlanUsage, hard_cap: int
) -> BreachForecast:
    remaining = max(hard_cap - usage.total_tokens, 0)
    # Already at/over the hard cap: breach is zero (or past) regardless of
    # whether the window establishes a burn rate.
    if remaining <= 0:
        return BreachForecast(
            provider=provider, daily_burn=0.0, remaining_tokens=0, days_to_cap=0.0
        )
    # A window that is a single instant (or absent) cannot establish a burn
    # rate; extrapolating from ~0 elapsed time produces an absurd daily burn
    # and a false imminent-breach WARN. Guard on a non-zero window.
    if (
        usage.window_start is None
        or usage.window_end is None
        or usage.window_end <= usage.window_start
    ):
        return BreachForecast(
            provider=provider, daily_burn=0.0, remaining_tokens=remaining
        )

    elapsed_days = (usage.window_end - usage.window_start).total_seconds() / 86400.0
    daily_burn = usage.total_tokens / elapsed_days
    if daily_burn <= 0:
        return BreachForecast(
            provider=provider, daily_burn=daily_burn, remaining_tokens=remaining
        )
    return BreachForecast(
        provider=provider,
        daily_burn=daily_burn,
        remaining_tokens=remaining,
        days_to_cap=remaining / daily_burn,
    )


def overall_verdict(findings: list[Finding]) -> str:
    """String verdict for CLI exit mapping: PASS/WARN/CRIT."""
    return max_finding_severity(list(findings))


def exit_code_for(verdict: str) -> int:
    """Map a verdict to a process exit code (0=pass,1=warn,2=crit/no-plan)."""
    return {Severity.PASS: 0, Severity.WARN: 1, Severity.CRIT: 2}.get(verdict, 2)