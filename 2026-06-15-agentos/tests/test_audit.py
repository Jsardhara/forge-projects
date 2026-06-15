"""Tests for audit logging."""

import pytest
from agentos.audit import AuditLogger
from agentos.models import Agent, AuditLog, Base, get_session, init_db


@pytest.fixture(autouse=True)
def setup_db(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(f"sqlite:///{db_path}")
    yield


@pytest.fixture
def sample_agent():
    session = get_session()
    agent = Agent(id="audit-agent", name="Audit Agent", agent_type="custom")
    session.add(agent)
    session.commit()
    session.close()
    return agent


def test_log_entry(sample_agent):
    logger = AuditLogger()
    entry = logger.log(
        agent_id="audit-agent",
        action="code_review",
        input_summary="Review PR #42",
        output_summary="Approved with minor comments",
        cost=0.02,
        tokens_in=500,
        tokens_out=200,
        policy_decision="allow",
    )
    assert entry.id is not None
    assert entry.action == "code_review"
    assert entry.policy_decision == "allow"


def test_get_logs(sample_agent):
    logger = AuditLogger()
    for i in range(5):
        logger.log(
            agent_id="audit-agent",
            action=f"action-{i}",
            cost=0.01 * (i + 1),
        )

    logs = logger.get_logs(agent_id="audit-agent", limit=3)
    assert len(logs) == 3
    # Most recent first
    assert logs[0].action == "action-4"


def test_get_log_count(sample_agent):
    logger = AuditLogger()
    for i in range(7):
        logger.log(agent_id="audit-agent", action=f"action-{i}")

    count = logger.get_log_count(agent_id="audit-agent")
    assert count == 7


def test_get_all_logs():
    session = get_session()
    for i in range(3):
        agent = Agent(id=f"agent-{i}", name=f"Agent {i}", agent_type="custom")
        session.add(agent)
    session.commit()
    session.close()

    logger = AuditLogger()
    for i in range(3):
        logger.log(agent_id=f"agent-{i}", action="test")

    all_logs = logger.get_logs()
    assert len(all_logs) == 3

    filtered = logger.get_logs(agent_id="agent-1")
    assert len(filtered) == 1
