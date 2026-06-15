"""Tests for the policy engine."""

import pytest
from agentos.models import Agent, Base, CostRecord, Policy, get_session, init_db
from agentos.policy import PolicyEngine


@pytest.fixture(autouse=True)
def setup_db(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(f"sqlite:///{db_path}")
    yield


@pytest.fixture
def sample_agent():
    session = get_session()
    agent = Agent(
        id="agent-1",
        name="Claude Code",
        agent_type="claude_code",
        max_spend_per_run=1.0,
        max_daily_spend=10.0,
    )
    session.add(agent)
    session.commit()
    session.close()
    return agent


def test_no_policies_allows(sample_agent):
    engine = PolicyEngine()
    result = engine.check_request(agent_id="agent-1")
    assert result.decision == "allow"
    assert result.is_allowed is True


def test_blocked_tool_blocks(sample_agent):
    session = get_session()
    policy = Policy(
        id="pol-block",
        name="Block rm",
        scope="global",
        blocked_tools="rm,exec",
    )
    session.add(policy)
    session.commit()
    session.close()

    engine = PolicyEngine()
    result = engine.check_request(
        agent_id="agent-1",
        tools_requested=["rm", "read_file"],
    )
    assert result.decision == "block"
    assert result.is_allowed is False
    assert any("Blocked tools" in r for r in result.reasons)


def test_allowed_tools_pass(sample_agent):
    session = get_session()
    policy = Policy(
        id="pol-block2",
        name="Block rm",
        scope="global",
        blocked_tools="rm",
    )
    session.add(policy)
    session.commit()
    session.close()

    engine = PolicyEngine()
    result = engine.check_request(
        agent_id="agent-1",
        tools_requested=["read_file", "write_file"],
    )
    assert result.decision == "allow"


def test_spend_limit_flags(sample_agent):
    session = get_session()
    policy = Policy(
        id="pol-spend",
        name="Spend Limit",
        scope="global",
        max_spend_per_run=0.5,
    )
    session.add(policy)
    session.commit()
    session.close()

    engine = PolicyEngine()
    result = engine.check_request(
        agent_id="agent-1",
        estimated_cost=1.0,
    )
    assert result.decision == "flag"
    assert any("exceeds" in r for r in result.reasons)


def test_daily_spend_blocks(sample_agent):
    session = get_session()
    policy = Policy(
        id="pol-daily",
        name="Daily Limit",
        scope="global",
        max_daily_spend=1.0,
    )
    session.add(policy)
    session.commit()

    # Add cost records that nearly exhaust the daily limit
    for _ in range(10):
        record = CostRecord(
            agent_id="agent-1",
            amount=0.09,
            description="Test spend",
        )
        session.add(record)
    session.commit()
    session.close()

    engine = PolicyEngine()
    result = engine.check_request(
        agent_id="agent-1",
        estimated_cost=0.5,
    )
    assert result.decision == "block"
    assert any("Daily spend" in r for r in result.reasons)


def test_approval_required_flags(sample_agent):
    session = get_session()
    policy = Policy(
        id="pol-approve",
        name="Approval Required",
        scope="global",
        require_approval_for="git_push,file_delete",
    )
    session.add(policy)
    session.commit()
    session.close()

    engine = PolicyEngine()
    result = engine.check_request(
        agent_id="agent-1",
        action_type="git_push",
    )
    assert result.decision == "flag"
    assert any("requires human approval" in r for r in result.reasons)


def test_agent_specific_policy_overrides(sample_agent):
    session = get_session()
    # Global policy: allow everything
    global_pol = Policy(
        id="pol-global",
        name="Global",
        scope="global",
        max_spend_per_run=10.0,
    )
    # Agent-specific policy: stricter
    agent_pol = Policy(
        id="pol-agent",
        name="Agent Specific",
        scope="agent",
        scope_id="agent-1",
        max_spend_per_run=0.5,
    )
    session.add_all([global_pol, agent_pol])
    session.commit()
    session.close()

    engine = PolicyEngine()
    result = engine.check_request(
        agent_id="agent-1",
        estimated_cost=0.8,
    )
    # Should flag because agent-specific policy has lower limit
    assert result.decision == "flag"
