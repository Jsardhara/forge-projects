"""Tests for Tournament bracket."""

import pytest
from agent_royale import AgentStatus, GameMode, IdentityRegistry
from agent_royale.arena import Arena
from agent_royale.bracket import Tournament


@pytest.fixture
def four_agents():
    reg = IdentityRegistry()
    a1 = reg.register("A1", "model/a")
    a2 = reg.register("A2", "model/b")
    a3 = reg.register("A3", "model/c")
    a4 = reg.register("A4", "model/d")
    return reg, [a1.agent_id, a2.agent_id, a3.agent_id, a4.agent_id]


@pytest.fixture
def eight_agents():
    reg = IdentityRegistry()
    ids = []
    for i in range(8):
        a = reg.register(f"Player{i}", f"model/p{i}")
        ids.append(a.agent_id)
    return reg, ids


class TestTournament:
    def test_create_tournament(self, four_agents):
        reg, ids = four_agents
        arena = Arena(reg)
        t = Tournament("Test Cup", GameMode.DEBATE, ids, arena)
        assert t.name == "Test Cup"
        assert len(t.rounds) == 1  # 4 players = 1 round of 2 matches
        assert len(t.rounds[0].match_ids) == 2

    def test_reject_non_power_of_two(self, four_agents):
        reg, ids = four_agents
        arena = Arena(reg)
        with pytest.raises(ValueError, match="power of 2"):
            Tournament("Bad", GameMode.DEBATE, ids[:3], arena)

    def test_reject_too_few(self):
        reg = IdentityRegistry()
        a1 = reg.register("Lonely", "model/x")
        arena = Arena(reg)
        with pytest.raises(ValueError, match="at least 2"):
            Tournament("Fail", GameMode.DEBATE, [a1.agent_id], arena)

    def test_current_round(self, four_agents):
        reg, ids = four_agents
        arena = Arena(reg)
        t = Tournament("Cup", GameMode.DEBATE, ids, arena)
        cr = t.current_round()
        assert cr is not None
        assert cr.round_number == 1

    def test_advance_round(self, four_agents):
        reg, ids = four_agents
        arena = Arena(reg)
        t = Tournament("Cup", GameMode.DEBATE, ids, arena)
        # Run all matches in round 1
        for mid in t.rounds[0].match_ids:
            m = arena.get_match(mid)
            responses = {pid: f"Response from {pid}" for pid in m.players}
            arena.run_match(m, responses)
        done = t.advance()
        assert not done  # tournament not over yet, round 2 created
        assert len(t.rounds) == 2

    def test_complete_tournament(self, four_agents):
        reg, ids = four_agents
        arena = Arena(reg)
        t = Tournament("Cup", GameMode.DEBATE, ids, arena)
        # Run all matches until tournament complete
        max_iters = 10
        for _ in range(max_iters):
            cr = t.current_round()
            if cr is None:
                break
            for mid in cr.match_ids:
                m = arena.get_match(mid)
                responses = {pid: f"Response from {pid}" for pid in m.players}
                arena.run_match(m, responses)
            if t.advance():
                break
        assert t.is_complete()
        assert t.champion_id is not None

    def test_eight_player_tournament(self, eight_agents):
        reg, ids = eight_agents
        arena = Arena(reg)
        t = Tournament("Big Cup", GameMode.CODING, ids, arena)
        assert len(t.rounds) == 1
        assert len(t.rounds[0].match_ids) == 4

    def test_standings_only_when_complete(self, four_agents):
        reg, ids = four_agents
        arena = Arena(reg)
        t = Tournament("Cup", GameMode.DEBATE, ids, arena)
        assert t.standings() == []  # not complete yet

    def test_agent_status_updates(self, four_agents):
        reg, ids = four_agents
        arena = Arena(reg)
        t = Tournament("Cup", GameMode.DEBATE, ids, arena)
        # Run round 1
        for mid in t.rounds[0].match_ids:
            m = arena.get_match(mid)
            responses = {pid: f"Response from {pid}" for pid in m.players}
            arena.run_match(m, responses)
        t.advance()
        # Some agents should be eliminated
        eliminated = [a for a in reg.list_all() if a.status == AgentStatus.ELIMINATED]
        assert len(eliminated) == 2  # 2 losers in round 1


class TestIntegration:
    """End-to-end: register → match → tournament → leaderboard."""

    def test_full_tourney_flow(self):
        reg = IdentityRegistry()
        names = ["Alpha", "Beta", "Gamma", "Delta"]
        ids = []
        for name in names:
            a = reg.register(name, f"model/{name.lower()}")
            ids.append(a.agent_id)

        arena = Arena(reg)
        t = Tournament("Championship", GameMode.DEBATE, ids, arena)

        # Run tournament
        for _ in range(10):
            cr = t.current_round()
            if cr is None:
                break
            for mid in cr.match_ids:
                m = arena.get_match(mid)
                responses = {pid: f"{pid} argues persuasively. Therefore, I win." for pid in m.players}
                arena.run_match(m, responses)
            if t.advance():
                break

        assert t.is_complete()
        assert t.champion_id is not None

        board = arena.get_leaderboard()
        assert len(board) == 4
        assert board[0]["rank"] == 1
        # Champion should be rank 1
        champion_entry = next(e for e in board if e["agent_id"] == t.champion_id)
        assert champion_entry["rank"] == 1
