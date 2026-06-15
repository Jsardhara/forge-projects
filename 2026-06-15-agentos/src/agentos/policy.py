"""Policy engine — evaluates agent requests against governance rules."""

from __future__ import annotations

from dataclasses import dataclass, field

from agentos.models import Policy, get_session


@dataclass
class PolicyCheckResult:
    decision: str  # "allow", "flag", "block"
    reasons: list[str] = field(default_factory=list)
    applied_policy_id: str | None = None
    max_spend_per_run: float | None = None
    max_daily_spend: float | None = None
    blocked_tools: list[str] = field(default_factory=list)
    requires_approval_for: list[str] = field(default_factory=list)

    @property
    def is_allowed(self) -> bool:
        return self.decision != "block"

    @property
    def is_flagged(self) -> bool:
        return self.decision == "flag"


class PolicyEngine:
    """Evaluates agent requests against active policies."""

    def check_request(
        self,
        agent_id: str,
        estimated_cost: float = 0.0,
        tools_requested: list[str] | None = None,
        action_type: str = "run",
    ) -> PolicyCheckResult:
        """Check if an agent request complies with active policies."""
        session = get_session()
        try:
            # Get agent-specific policies first, then global
            policies: list[Policy] = (
                session.query(Policy)
                .filter(
                    Policy.is_active == True,
                )
                .filter(
                    (Policy.scope == "global")
                    | ((Policy.scope == "agent") & (Policy.scope_id == agent_id))
                )
                .order_by(
                    # Agent-specific policies take priority
                    Policy.scope.desc()
                )
                .all()
            )

            if not policies:
                return PolicyCheckResult(decision="allow")

            # Merge all applicable policies (most restrictive wins)
            result = PolicyCheckResult(decision="allow")
            all_blocked_tools: set[str] = set()
            all_approval_actions: set[str] = set()
            min_spend_per_run: float | None = None
            min_daily_spend: float | None = None

            for policy in policies:
                # Check blocked tools
                if policy.blocked_tools:
                    tools = [
                        t.strip()
                        for t in policy.blocked_tools.split(",")
                        if t.strip()
                    ]
                    all_blocked_tools.update(tools)

                # Check approval requirements
                if policy.require_approval_for:
                    actions = [
                        a.strip()
                        for a in policy.require_approval_for.split(",")
                        if a.strip()
                    ]
                    all_approval_actions.update(actions)

                # Check spend limits (most restrictive)
                if policy.max_spend_per_run is not None:
                    if min_spend_per_run is None:
                        min_spend_per_run = policy.max_spend_per_run
                    else:
                        min_spend_per_run = min(
                            min_spend_per_run, policy.max_spend_per_run
                        )

                if policy.max_daily_spend is not None:
                    if min_daily_spend is None:
                        min_daily_spend = policy.max_daily_spend
                    else:
                        min_daily_spend = min(
                            min_daily_spend, policy.max_daily_spend
                        )

            result.max_spend_per_run = min_spend_per_run
            result.max_daily_spend = min_daily_spend
            result.blocked_tools = sorted(all_blocked_tools)
            result.requires_approval_for = sorted(all_approval_actions)

            # Evaluate blocked tools
            if tools_requested and all_blocked_tools:
                blocked_requested = [
                    t for t in tools_requested if t in all_blocked_tools
                ]
                if blocked_requested:
                    result.decision = "block"
                    result.reasons.append(
                        f"Blocked tools requested: {', '.join(blocked_requested)}"
                    )

            # Evaluate spend per run
            if min_spend_per_run is not None and estimated_cost > min_spend_per_run:
                if result.decision != "block":
                    result.decision = "flag"
                result.reasons.append(
                    f"Estimated cost ${estimated_cost:.4f} exceeds "
                    f"per-run limit ${min_spend_per_run:.4f}"
                )

            # Evaluate daily spend
            if min_daily_spend is not None:
                from datetime import datetime, timezone as tz

                now = datetime.now(tz.utc)
                today_start = now.replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                from agentos.models import CostRecord

                daily_spend = (
                    session.query(CostRecord)
                    .filter(CostRecord.agent_id == agent_id)
                    .filter(CostRecord.created_at >= today_start)
                )
                total_daily = sum(r.amount for r in daily_spend.all()) + estimated_cost

                if total_daily > min_daily_spend:
                    result.decision = "block"
                    result.reasons.append(
                        f"Daily spend ${total_daily:.4f} would exceed "
                        f"limit ${min_daily_spend:.4f}"
                    )

            # Evaluate approval requirements
            if action_type in all_approval_actions:
                if result.decision == "allow":
                    result.decision = "flag"
                result.reasons.append(
                    f"Action '{action_type}' requires human approval"
                )

            return result
        finally:
            session.close()
