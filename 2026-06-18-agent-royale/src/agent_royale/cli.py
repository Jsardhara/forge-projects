"""CLI for Agent Royale — register agents, run matches, view leaderboard."""

from __future__ import annotations

import argparse
import json
import sys

from . import GameMode, IdentityRegistry
from .arena import Arena
from .bracket import Tournament


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent Royale — AI Agent Battle Platform")
    sub = parser.add_subparsers(dest="command")

    # Register
    reg = sub.add_parser("register", help="Register a new agent")
    reg.add_argument("name", help="Agent name")
    reg.add_argument("model_id", help="Model ID (e.g., openai/gpt-4o)")

    # List
    sub.add_parser("list", help="List all registered agents")

    # Match
    match_cmd = sub.add_parser("match", help="Run a single match")
    match_cmd.add_argument("--mode", choices=["debate", "coding", "trivia"], default="debate")
    match_cmd.add_argument("--players", nargs="+", required=True, help="Agent IDs")

    # Tournament
    tourney = sub.add_parser("tournament", help="Run a tournament")
    tourney.add_argument("name", help="Tournament name")
    tourney.add_argument("--mode", choices=["debate", "coding", "trivia"], default="debate")
    tourney.add_argument("--players", nargs="+", required=True, help="Agent IDs (power of 2)")

    # Leaderboard
    sub.add_parser("leaderboard", help="Show current leaderboard")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    registry = IdentityRegistry()
    arena = Arena(registry)

    if args.command == "register":
        agent = registry.register(args.name, args.model_id)
        print(f"Registered: {agent.name} ({agent.agent_id}) — {agent.model_id}")

    elif args.command == "list":
        agents = registry.list_all()
        if not agents:
            print("No agents registered.")
        for a in agents:
            print(f"  {a.agent_id}: {a.name} ({a.model_id}) — score={a.score:.1f} W{a.wins}/L{a.losses}")

    elif args.command == "match":
        mode = GameMode(args.mode)
        m = arena.create_match(mode, args.players)
        print(f"Match created: {m.match_id} ({m.mode.value})")
        print(f"Players: {', '.join(m.players)}")
        print("Use run-match with responses to complete.")

    elif args.command == "tournament":
        mode = GameMode(args.mode)
        t = Tournament(args.name, mode, args.players, arena)
        print(f"Tournament '{t.name}' created with {len(t.player_ids)} players")
        print(f"Rounds: {len(t.rounds)}")
        for r in t.rounds:
            print(f"  Round {r.round_number}: {len(r.match_ids)} matches")

    elif args.command == "leaderboard":
        board = arena.get_leaderboard()
        if not board:
            print("No agents on the leaderboard.")
        for entry in board:
            print(f"  #{entry['rank']} {entry['name']} — {entry['score']:.1f} pts ({entry['wins']}W/{entry['losses']}L)")


if __name__ == "__main__":
    main()
