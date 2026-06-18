"""Tournament bracket — elimination rounds between agents."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timezone

from . import AgentStatus, GameMode, Match


@dataclass
class BracketRound:
    round_number: int
    match_ids: list[str] = field(default_factory=list)
    completed: bool = False


class Tournament:
    """Single-elimination tournament between agents."""

    def __init__(
        self,
        name: str,
        mode: GameMode,
        player_ids: list[str],
        arena,  # Arena instance
    ) -> None:
        if len(player_ids) < 2:
            raise ValueError("Tournament requires at least 2 players")
        if len(player_ids) & (len(player_ids) - 1) != 0:
            raise ValueError("Player count must be a power of 2 (2, 4, 8, 16...)")

        self.name = name
        self.mode = mode
        self.player_ids = list(player_ids)
        self.arena = arena
        self.rounds: list[BracketRound] = []
        self.champion_id: str | None = None
        self.created_at = datetime.now(timezone.utc)
        self._build_bracket()

    def _build_bracket(self) -> None:
        """Shuffle players and create initial round."""
        shuffled = self.player_ids[:]
        random.shuffle(shuffled)
        round1 = BracketRound(round_number=1)
        for i in range(0, len(shuffled), 2):
            match = self.arena.create_match(
                mode=self.mode,
                player_ids=[shuffled[i], shuffled[i + 1]],
            )
            round1.match_ids.append(match.match_id)
        self.rounds.append(round1)

    def current_round(self) -> BracketRound | None:
        for r in self.rounds:
            if not r.completed:
                return r
        return None

    def advance(self) -> bool:
        """Advance to the next round. Returns True if tournament complete."""
        cr = self.current_round()
        if cr is None:
            return True  # tournament over

        # Check all matches in current round are complete
        for mid in cr.match_ids:
            m = self.arena.get_match(mid)
            if m is None or not m.completed:
                return False  # not ready to advance

        cr.completed = True

        # Collect winners
        winners: list[str] = []
        for mid in cr.match_ids:
            m = self.arena.get_match(mid)
            if m and m.winner_id:
                winners.append(m.winner_id)
                # Re-register eliminated agents for display but mark winners
                for pid in m.players:
                    if pid != m.winner_id:
                        agent = self.arena.registry.get(pid)
                        if agent:
                            agent.status = AgentStatus.ELIMINATED

        if len(winners) <= 1:
            self.champion_id = winners[0] if winners else None
            return True  # tournament over

        # Reset winners to REGISTERED so they can play the next round
        for wid in winners:
            agent = self.arena.registry.get(wid)
            if agent and agent.status == AgentStatus.WINNER:
                agent.status = AgentStatus.REGISTERED

        # Create next round
        next_round_num = cr.round_number + 1
        next_round = BracketRound(round_number=next_round_num)
        for i in range(0, len(winners), 2):
            match = self.arena.create_match(
                mode=self.mode,
                player_ids=[winners[i], winners[i + 1]],
            )
            next_round.match_ids.append(match.match_id)
        self.rounds.append(next_round)
        return False

    def is_complete(self) -> bool:
        return self.champion_id is not None

    def standings(self) -> list[dict]:
        """Return tournament standings with ranks."""
        if not self.is_complete():
            return []
        # Champion first, then by round eliminated (later = better)
        leaderboard = self.arena.get_leaderboard()
        return leaderboard
