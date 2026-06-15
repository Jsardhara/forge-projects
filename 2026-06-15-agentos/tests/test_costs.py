"""Tests for cost tracking."""

import pytest
from agentos.costs import CostTracker
from agentos.models import Agent, Base, CostRecord, get_session, init_db


@pytest.fixture(autouse=True)
def setup_db(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(f"sqlite:///{db_path}")
    yield


@pytest.fixture
def sample_agent():
    session = get_session()
    agent = Agent(id="cost-agent", name="Cost Agent", agent_type="codex")
    session.add(agent)
    session.commit()
    session.close()
    return agent


def test_record_cost(sample_agent):
    tracker = CostTracker()
    record = tracker.record_cost(
        agent_id="cost-agent",
        amount=0.05,
        tokens_in=1000,
        tokens_out=500,
        description="Test run",
    )
    assert record.id is not None
    assert record.amount == 0.05


def test_get_agent_cost(sample_agent):
    tracker = CostTracker()
    tracker.record_cost(agent_id="cost-agent", amount=0.03, tokens_in=500, tokens_out=200)
    tracker.record_cost(agent_id="cost-agent", amount=0.07, tokens_in=800, tokens_out=400)

    result = tracker.get_agent_cost("cost-agent")
    assert result["total_cost"] == 0.10
    assert result["tokens_in"] == 1300
    assert result["tokens_out"] == 600
    assert result["record_count"] == 2


def test_get_summary(sample_agent):
    tracker = CostTracker()
    tracker.record_cost(agent_id="cost-agent", amount=0.15, tokens_in=2000, tokens_out=1000)

    summary = tracker.get_summary()
    assert summary.total_cost == 0.15
    assert summary.total_tokens_in == 2000
    assert summary.total_tokens_out == 1000
    assert summary.agent_count >= 1


def test_top_spenders():
    session = get_session()
    for i in range(3):
        agent = Agent(id=f"agent-{i}", name=f"Agent {i}", agent_type="custom")
        session.add(agent)
    session.commit()
    session.close()

    tracker = CostTracker()
    tracker.record_cost(agent_id="agent-0", amount=0.50)
    tracker.record_cost(agent_id="agent-1", amount=0.30)
    tracker.record_cost(agent_id="agent-2", amount=0.10)

    summary = tracker.get_summary()
    assert len(summary.top_spenders) == 3
    assert summary.top_spenders[0]["agent_id"] == "agent-0"
    assert summary.top_spenders[0]["total_cost"] == 0.50
