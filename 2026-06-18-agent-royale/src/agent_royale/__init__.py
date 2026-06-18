"""Agent Royale — Core arena engine for competitive AI agent benchmarking."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class AgentStatus(str, Enum):
    REGISTERED = "registered"
    PLAYING = "playing"
    ELIMINATED = "eliminated"
    WINNER = "winner"


class GameMode(str, Enum):
    DEBATE = "debate"
    CODING = "coding"
    TRIVIA = "trivia"


@dataclass
class Agent:
    name: str
    model_id: str
    agent_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    status: AgentStatus = AgentStatus.REGISTERED
    score: float = 0.0
    wins: int = 0
    losses: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def win_rate(self) -> float:
        total = self.wins + self.losses
        return self.wins / total if total > 0 else 0.0

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "model_id": self.model_id,
            "status": self.status.value,
            "score": round(self.score, 2),
            "wins": self.wins,
            "losses": self.losses,
            "win_rate": round(self.win_rate, 3),
        }


@dataclass
class Match:
    match_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    mode: GameMode = GameMode.DEBATE
    players: list[str] = field(default_factory=list)
    winner_id: str | None = None
    scores: dict[str, float] = field(default_factory=dict)
    completed: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None


class IdentityRegistry:
    """Register and manage competing agents."""

    def __init__(self) -> None:
        self._agents: dict[str, Agent] = {}

    def register(self, name: str, model_id: str) -> Agent:
        agent = Agent(name=name, model_id=model_id)
        self._agents[agent.agent_id] = agent
        return agent

    def get(self, agent_id: str) -> Agent | None:
        return self._agents.get(agent_id)

    def list_all(self) -> list[Agent]:
        return list(self._agents.values())

    def list_active(self) -> list[Agent]:
        return [a for a in self._agents.values() if a.status == AgentStatus.REGISTERED]

    def update_status(self, agent_id: str, status: AgentStatus) -> Agent:
        agent = self._agents[agent_id]
        agent.status = status
        return agent

    def remove(self, agent_id: str) -> bool:
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False

    def count(self) -> int:
        return len(self._agents)
