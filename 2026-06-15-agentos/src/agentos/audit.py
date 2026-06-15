"""Audit logging for agent actions."""

from __future__ import annotations

from datetime import datetime, timezone

from agentos.models import AuditLog, get_session


class AuditLogger:
    """Records and queries agent action audit logs."""

    def log(
        self,
        agent_id: str,
        action: str,
        input_summary: str = "",
        output_summary: str = "",
        cost: float = 0.0,
        tokens_in: int = 0,
        tokens_out: int = 0,
        policy_decision: str = "allow",
        policy_reason: str = "",
    ) -> AuditLog:
        """Record an audit log entry."""
        session = get_session()
        try:
            entry = AuditLog(
                agent_id=agent_id,
                action=action,
                input_summary=input_summary[:2000] if input_summary else "",
                output_summary=output_summary[:2000] if output_summary else "",
                cost=cost,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                policy_decision=policy_decision,
                policy_reason=policy_reason[:1000] if policy_reason else "",
            )
            session.add(entry)
            session.commit()
            session.refresh(entry)
            return entry
        finally:
            session.close()

    def get_logs(
        self,
        agent_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        """Get audit log entries, optionally filtered by agent."""
        session = get_session()
        try:
            query = session.query(AuditLog)
            if agent_id:
                query = query.filter(AuditLog.agent_id == agent_id)
            return (
                query.order_by(AuditLog.created_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )
        finally:
            session.close()

    def get_log_count(self, agent_id: str | None = None) -> int:
        """Get total count of audit log entries."""
        session = get_session()
        try:
            query = session.query(AuditLog)
            if agent_id:
                query = query.filter(AuditLog.agent_id == agent_id)
            return query.count()
        finally:
            session.close()
