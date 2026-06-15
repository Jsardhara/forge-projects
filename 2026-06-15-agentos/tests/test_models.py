"""Tests for AgentOS models and database."""

import pytest
from agentos.models import Agent, AuditLog, Base, CostRecord, Policy, get_session, init_db


@pytest.fixture(autouse=True)
def setup_db(tmp_path):
    """Use a fresh in-memory SQLite database for each test."""
    db_path = tmp_path / "test.db"
    init_db(f"sqlite:///{db_path}")
    yield


def test_init_db_creates_tables(tmp_path):
    db_path = tmp_path / "test2.db"
    init_db(f"sqlite:///{db_path}")
    assert db_path.exists()


def test_create_agent():
    session = get_session()
    agent = Agent(
        id="test-agent-1",
        name="Test Agent",
        agent_type="claude_code",
        max_spend_per_run=5.0,
        max_daily_spend=50.0,
    )
    session.add(agent)
    session.commit()

    result = session.query(Agent).filter(Agent.id == "test-agent-1").first()
    assert result is not None
    assert result.name == "Test Agent"
    assert result.agent_type == "claude_code"
    assert result.max_spend_per_run == 5.0
    assert result.is_active is True
    session.close()


def test_create_policy():
    session = get_session()
    policy = Policy(
        id="pol-1",
        name="Block Dangerous Tools",
        scope="global",
        blocked_tools="rm,exec,eval",
        require_approval_for="git_push,file_delete",
    )
    session.add(policy)
    session.commit()

    result = session.query(Policy).filter(Policy.id == "pol-1").first()
    assert result is not None
    assert result.blocked_tools == "rm,exec,eval"
    assert result.is_active is True
    session.close()


def test_agent_cost_record():
    session = get_session()
    agent = Agent(id="cost-agent", name="Cost Agent", agent_type="codex")
    session.add(agent)
    session.commit()

    record = CostRecord(
        agent_id="cost-agent",
        amount=0.05,
        tokens_in=1000,
        tokens_out=500,
        description="Test run",
    )
    session.add(record)
    session.commit()

    records = (
        session.query(CostRecord).filter(CostRecord.agent_id == "cost-agent").all()
    )
    assert len(records) == 1
    assert records[0].amount == 0.05
    session.close()


def test_audit_log():
    session = get_session()
    agent = Agent(id="audit-agent", name="Audit Agent", agent_type="custom")
    session.add(agent)
    session.commit()

    entry = AuditLog(
        agent_id="audit-agent",
        action="code_review",
        cost=0.02,
        tokens_in=500,
        tokens_out=200,
        policy_decision="allow",
    )
    session.add(entry)
    session.commit()

    logs = (
        session.query(AuditLog).filter(AuditLog.agent_id == "audit-agent").all()
    )
    assert len(logs) == 1
    assert logs[0].action == "code_review"
    assert logs[0].policy_decision == "allow"
    session.close()
