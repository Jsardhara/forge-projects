"""Database models and session management."""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker


class Base(DeclarativeBase):
    pass


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    agent_type = Column(String, nullable=False)  # claude_code, codex, custom
    description = Column(Text, default="")
    max_spend_per_run = Column(Float, default=1.0)  # USD
    max_daily_spend = Column(Float, default=10.0)  # USD
    is_active = Column(Boolean, default=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    audit_logs = relationship("AuditLog", back_populates="agent")
    cost_records = relationship("CostRecord", back_populates="agent")


class Policy(Base):
    __tablename__ = "policies"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    scope = Column(String, default="global")  # global, agent, project
    scope_id = Column(String, nullable=True)  # agent_id or project_id
    max_spend_per_run = Column(Float, nullable=True)
    max_daily_spend = Column(Float, nullable=True)
    blocked_tools = Column(Text, default="")  # comma-separated list
    require_approval_for = Column(Text, default="")  # comma-separated actions
    is_active = Column(Boolean, default=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    action = Column(String, nullable=False)
    input_summary = Column(Text, default="")
    output_summary = Column(Text, default="")
    cost = Column(Float, default=0.0)
    tokens_in = Column(Integer, default=0)
    tokens_out = Column(Integer, default=0)
    policy_decision = Column(String, default="allow")  # allow, flag, block
    policy_reason = Column(Text, default="")
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    agent = relationship("Agent", back_populates="audit_logs")


class CostRecord(Base):
    __tablename__ = "cost_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    amount = Column(Float, nullable=False)  # USD
    tokens_in = Column(Integer, default=0)
    tokens_out = Column(Integer, default=0)
    description = Column(Text, default="")
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    agent = relationship("Agent", back_populates="cost_records")


# Database engine and session
_engine = None
_session_factory = None


def init_db(db_url: str = "sqlite:///./agentos.db"):
    global _engine, _session_factory
    _engine = create_engine(db_url, connect_args={"check_same_thread": False})
    _session_factory = sessionmaker(bind=_engine)
    Base.metadata.create_all(_engine)


def get_session() -> Session:
    if _session_factory is None:
        init_db()
    return _session_factory()
