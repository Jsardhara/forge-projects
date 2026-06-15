"""Cost tracking and analytics for AI agent spending."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from agentos.models import Agent, CostRecord, get_session


@dataclass
class CostSummary:
    total_cost: float = 0.0
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    agent_count: int = 0
    daily_cost: float = 0.0
    top_spenders: list[dict] = field(default_factory=list)


class CostTracker:
    """Tracks and analyzes AI agent spending."""

    def record_cost(
        self,
        agent_id: str,
        amount: float,
        tokens_in: int = 0,
        tokens_out: int = 0,
        description: str = "",
    ) -> CostRecord:
        """Record a cost entry for an agent."""
        session = get_session()
        try:
            record = CostRecord(
                agent_id=agent_id,
                amount=amount,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                description=description,
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            return record
        finally:
            session.close()

    def get_agent_cost(self, agent_id: str) -> dict:
        """Get cost summary for a specific agent."""
        session = get_session()
        try:
            records = (
                session.query(CostRecord)
                .filter(CostRecord.agent_id == agent_id)
                .all()
            )
            total = sum(r.amount for r in records)
            tokens_in = sum(r.tokens_in for r in records)
            tokens_out = sum(r.tokens_out for r in records)

            from datetime import timezone as tz

            now = datetime.now(tz.utc)
            today_start = now.replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            daily_records = []
            for r in records:
                created = r.created_at
                if created.tzinfo is None:
                    created = created.replace(tzinfo=tz.utc)
                if created >= today_start:
                    daily_records.append(r)
            daily = sum(r.amount for r in daily_records)

            return {
                "agent_id": agent_id,
                "total_cost": round(total, 4),
                "daily_cost": round(daily, 4),
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "record_count": len(records),
            }
        finally:
            session.close()

    def get_summary(self) -> CostSummary:
        """Get overall cost summary across all agents."""
        session = get_session()
        try:
            agents = session.query(Agent).filter(Agent.is_active == True).all()
            records = session.query(CostRecord).all()

            total_cost = sum(r.amount for r in records)
            total_tokens_in = sum(r.tokens_in for r in records)
            total_tokens_out = sum(r.tokens_out for r in records)

            from datetime import timezone as tz

            now = datetime.now(tz.utc)
            today_start = now.replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            daily_records = []
            for r in records:
                created = r.created_at
                if created.tzinfo is None:
                    created = created.replace(tzinfo=tz.utc)
                if created >= today_start:
                    daily_records.append(r)
            daily_cost = sum(r.amount for r in daily_records)

            # Top spenders
            agent_costs: dict[str, float] = {}
            for r in records:
                agent_costs[r.agent_id] = agent_costs.get(r.agent_id, 0) + r.amount

            top_spenders = sorted(
                [
                    {"agent_id": aid, "total_cost": round(cost, 4)}
                    for aid, cost in agent_costs.items()
                ],
                key=lambda x: x["total_cost"],
                reverse=True,
            )[:5]

            return CostSummary(
                total_cost=round(total_cost, 4),
                total_tokens_in=total_tokens_in,
                total_tokens_out=total_tokens_out,
                agent_count=len(agents),
                daily_cost=round(daily_cost, 4),
                top_spenders=top_spenders,
            )
        finally:
            session.close()
