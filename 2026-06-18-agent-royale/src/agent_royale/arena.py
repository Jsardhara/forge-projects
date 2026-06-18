"""Arena engine — runs competitive matches between AI agents."""

from __future__ import annotations

import random
from datetime import datetime, timezone

from . import Agent, AgentStatus, GameMode, IdentityRegistry, Match


class ScoringEngine:
    """Score agent responses across different game modes."""

    @staticmethod
    def score_debate(response: str, criteria: list[str] | None = None) -> float:
        """Score a debate response on clarity, reasoning, and persuasiveness (0-100)."""
        if not response or not response.strip():
            return 0.0
        # Heuristic scoring: length + structure + keyword presence
        score = min(len(response) / 10, 40)  # up to 40 pts for length
        if "\n" in response:  # structured response
            score += 15
        if any(word in response.lower() for word in ["because", "therefore", "however", "evidence"]):
            score += 20
        if any(word in response.lower() for word in ["first", "second", "third", "finally"]):
            score += 15
        # Randomness simulates LLM judge variance
        score += random.uniform(0, 10)
        return min(score, 100.0)

    @staticmethod
    def score_coding(response: str, test_cases: list[str] | None = None) -> float:
        """Score a coding response on correctness and style (0-100)."""
        if not response or not response.strip():
            return 0.0
        score = 0.0
        if "def " in response or "class " in response or "function" in response:
            score += 30
        if "```" in response:  # code block formatting
            score += 15
        if "test" in response.lower() or "assert" in response.lower():
            score += 20
        if "#" in response or "//" in response:  # comments
            score += 10
        if "error" not in response.lower() and "exception" not in response.lower():
            score += 10
        score += random.uniform(0, 15)
        return min(score, 100.0)

    @staticmethod
    def score_trivia(response: str, correct_answer: str | None = None) -> float:
        """Score a trivia response: 100 for correct, 00 for wrong, partial for close."""
        if not response or not response.strip():
            return 0.0
        if correct_answer:
            response_clean = response.strip().lower().rstrip(".")
            answer_clean = correct_answer.strip().lower().rstrip(".")
            if response_clean == answer_clean:
                return 100.0
            # Partial credit for containing the answer
            if answer_clean in response_clean or response_clean in answer_clean:
                return 50.0
            return 0.0
        # No answer key — score on confidence markers
        score = 30.0
        if any(word in response.lower() for word in ["the answer is", "correct answer", "definitely"]):
            score += 20
        score += random.uniform(0, 50)
        return min(score, 100.0)


class Arena:
    """Run competitive matches between registered agents."""

    def __init__(self, registry: IdentityRegistry) -> None:
        self.registry = registry
        self.scoring = ScoringEngine()
        self._matches: list[Match] = []

    def create_match(self, mode: GameMode, player_ids: list[str]) -> Match:
        if len(player_ids) < 2:
            raise ValueError("Need at least 2 players for a match")
        for pid in player_ids:
            agent = self.registry.get(pid)
            if agent is None:
                raise ValueError(f"Unknown agent: {pid}")
            if agent.status != AgentStatus.REGISTERED:
                raise ValueError(f"Agent {pid} is not available (status: {agent.status.value})")
        match = Match(mode=mode, players=player_ids)
        self._matches.append(match)
        return match

    def run_match(
        self,
        match: Match,
        responses: dict[str, str],
        correct_answer: str | None = None,
    ) -> Match:
        """Score all responses and determine the winner."""
        if match.completed:
            raise ValueError(f"Match {match.match_id} already completed")

        scores: dict[str, float] = {}
        for pid in match.players:
            response = responses.get(pid, "")
            if match.mode == GameMode.DEBATE:
                scores[pid] = self.scoring.score_debate(response)
            elif match.mode == GameMode.CODING:
                scores[pid] = self.scoring.score_coding(response)
            elif match.mode == GameMode.TRIVIA:
                scores[pid] = self.scoring.score_trivia(response, correct_answer)
            else:
                scores[pid] = 0.0

        match.scores = scores
        match.winner_id = max(scores, key=scores.get)  # type: ignore[arg-type]
        match.completed = True
        match.completed_at = datetime.now(timezone.utc)

        # Update agent records
        for pid in match.players:
            agent = self.registry.get(pid)
            if agent is None:
                continue
            agent.score += scores.get(pid, 0)
            if pid == match.winner_id:
                agent.wins += 1
                agent.status = AgentStatus.WINNER
            else:
                agent.losses += 1
                agent.status = AgentStatus.ELIMINATED

        return match

    def get_match(self, match_id: str) -> Match | None:
        for m in self._matches:
            if m.match_id == match_id:
                return m
        return None

    def list_matches(self) -> list[Match]:
        return list(self._matches)

    def get_leaderboard(self) -> list[dict]:
        """Return agents sorted by score descending."""
        agents = self.registry.list_all()
        sorted_agents = sorted(agents, key=lambda a: (-a.score, -a.win_rate))
        return [
            {**a.to_dict(), "rank": i + 1}
            for i, a in enumerate(sorted_agents)
        ]
