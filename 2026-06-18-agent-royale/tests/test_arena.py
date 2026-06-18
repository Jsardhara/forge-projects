"""Tests for Arena and ScoringEngine."""

import pytest
from agent_royale import AgentStatus, GameMode, IdentityRegistry
from agent_royale.arena import Arena, ScoringEngine


@pytest.fixture
def registry():
    reg = IdentityRegistry()
    reg.register("Alice", "openai/gpt-4o")
    reg.register("Bob", "anthropic/claude-opus-4")
    return reg


@pytest.fixture
def arena(registry):
    return Arena(registry)


class TestScoringEngine:
    def test_debate_empty_response(self):
        assert ScoringEngine.score_debate("") == 0.0

    def test_debate_short_response(self):
        score = ScoringEngine.score_debate("I think so.")
        assert 0.0 <= score <= 100.0

    def test_debate_structured_response(self):
        response = "First, the evidence shows.\nSecond, we must consider.\nTherefore, I conclude."
        score = ScoringEngine.score_debate(response)
        assert score > 30.0

    def test_debate_with_reasoning_keywords(self):
        response = "Because the data shows X, however Y is also true. The evidence supports Z."
        score = ScoringEngine.score_debate(response)
        assert score > 25.0

    def test_coding_empty_response(self):
        assert ScoringEngine.score_coding("") == 0.0

    def test_coding_with_function(self):
        score = ScoringEngine.score_coding("def hello(): return 'world'")
        assert score > 25.0

    def test_coding_with_code_block(self):
        score = ScoringEngine.score_coding("```python\ndef solve():\n    pass\n```")
        assert score > 30.0

    def test_coding_with_tests(self):
        score = ScoringEngine.score_coding("def add(a, b): return a + b\nassert add(1, 2) == 3")
        assert score > 40.0

    def test_trivia_empty_response(self):
        assert ScoringEngine.score_trivia("") == 0.0

    def test_trivia_correct_answer(self):
        score = ScoringEngine.score_trivia("Paris", "Paris")
        assert score == 100.0

    def test_trivia_wrong_answer(self):
        score = ScoringEngine.score_trivia("London", "Paris")
        assert score == 0.0

    def test_trivia_partial_credit(self):
        score = ScoringEngine.score_trivia("The city of Paris in France", "Paris")
        assert score == 50.0

    def test_trivia_no_answer_key(self):
        score = ScoringEngine.score_trivia("The answer is definitely 42.")
        assert 30.0 <= score <= 100.0


class TestArena:
    def test_create_match(self, arena, registry):
        agents = registry.list_active()
        match = arena.create_match(GameMode.DEBATE, [a.agent_id for a in agents[:2]])
        assert match.mode == GameMode.DEBATE
        assert len(match.players) == 2
        assert not match.completed

    def test_create_match_too_few_players(self, arena, registry):
        agents = registry.list_active()
        with pytest.raises(ValueError, match="at least 2"):
            arena.create_match(GameMode.DEBATE, [agents[0].agent_id])

    def test_create_match_unknown_agent(self, arena, registry):
        agents = registry.list_active()
        with pytest.raises(ValueError, match="Unknown agent"):
            arena.create_match(GameMode.DEBATE, [agents[0].agent_id, "fake-id"])

    def test_run_debate_match(self, arena, registry):
        agents = registry.list_active()
        ids = [a.agent_id for a in agents[:2]]
        match = arena.create_match(GameMode.DEBATE, ids)
        responses = {
            ids[0]: "I believe X because the evidence shows Y. Therefore, Z is correct.",
            ids[1]: "I disagree. However, I see your point.",
        }
        result = arena.run_match(match, responses)
        assert result.completed
        assert result.winner_id is not None
        assert result.winner_id in ids
        assert len(result.scores) == 2

    def test_run_coding_match(self, arena, registry):
        agents = registry.list_active()
        ids = [a.agent_id for a in agents[:2]]
        match = arena.create_match(GameMode.CODING, ids)
        responses = {
            ids[0]: "def solve(nums):\n    # Two pointer approach\n    return sum(nums)\nassert solve([1,2]) == 3",
            ids[1]: "function solve(n) { return n; }",
        }
        result = arena.run_match(match, responses)
        assert result.completed
        assert result.winner_id is not None

    def test_run_trivia_match(self, arena, registry):
        agents = registry.list_active()
        ids = [a.agent_id for a in agents[:2]]
        match = arena.create_match(GameMode.TRIVIA, ids)
        responses = {ids[0]: "Paris", ids[1]: "London"}
        result = arena.run_match(match, responses, correct_answer="Paris")
        assert result.completed
        assert result.winner_id == ids[0]

    def test_cannot_run_completed_match(self, arena, registry):
        agents = registry.list_active()
        ids = [a.agent_id for a in agents[:2]]
        match = arena.create_match(GameMode.DEBATE, ids)
        arena.run_match(match, {ids[0]: "A", ids[1]: "B"})
        with pytest.raises(ValueError, match="already completed"):
            arena.run_match(match, {ids[0]: "C", ids[1]: "D"})

    def test_list_matches(self, arena, registry):
        agents = registry.list_active()
        ids = [a.agent_id for a in agents[:2]]
        arena.create_match(GameMode.DEBATE, ids)
        assert len(arena.list_matches()) == 1

    def test_get_match(self, arena, registry):
        agents = registry.list_active()
        ids = [a.agent_id for a in agents[:2]]
        match = arena.create_match(GameMode.DEBATE, ids)
        found = arena.get_match(match.match_id)
        assert found is not None
        assert found.match_id == match.match_id

    def test_leaderboard(self, arena, registry):
        agents = registry.list_active()
        ids = [a.agent_id for a in agents[:2]]
        match = arena.create_match(GameMode.DEBATE, ids)
        arena.run_match(match, {ids[0]: "A" * 200, ids[1]: "B"})
        board = arena.get_leaderboard()
        assert len(board) >= 1
        assert "rank" in board[0]
        assert "score" in board[0]
