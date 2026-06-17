"""CLI for AgentIAM."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone


def _fmt_ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def _get_iam(args: argparse.Namespace) -> "AgentIAM":
    from agentiam import AgentIAM
    ttl = getattr(args, "credential_ttl", 3600)
    return AgentIAM(default_credential_ttl=ttl)


def cmd_register(args: argparse.Namespace) -> None:
    from agentiam import AgentIAM
    iam = AgentIAM(default_credential_ttl=args.credential_ttl)
    agent = iam.registry.register(
        name=args.name,
        owner=args.owner,
        description=args.description or "",
        model_id=args.model_id or "",
        scopes=args.scopes or [],
    )
    iam.audit.record(agent.agent_id, "register", "identity", "allow")
    print(f"Registered agent: {agent.agent_id}")
    print(f"  Name:   {agent.name}")
    print(f"  Owner:  {agent.owner}")
    print(f"  Status: {agent.status.value}")
    print(f"  FP:     {agent.fingerprint()}")


def cmd_list(args: argparse.Namespace) -> None:
    from agentiam import AgentIAM, AgentStatus
    iam = AgentIAM(default_credential_ttl=args.credential_ttl)
    status_filter = None
    if args.status:
        status_filter = AgentStatus(args.status)
    agents = iam.registry.list_agents(status=status_filter)
    if not agents:
        print("No agents registered.")
        return
    for a in agents:
        print(f"{a.agent_id}  {a.name:<30}  {a.owner:<20}  {a.status.value}")


def cmd_issue(args: argparse.Namespace) -> None:
    from agentiam import AgentIAM
    iam = AgentIAM(default_credential_ttl=args.credential_ttl)
    try:
        cred = iam.issue_credential(args.agent_id, scopes=args.scopes or [], ttl=args.ttl)
    except (KeyError, PermissionError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"Credential issued: {cred.credential_id}")
    print(f"  Token:     {cred.token[:24]}...")
    print(f"  Scopes:    {', '.join(cred.scopes) or '(none)'}")
    print(f"  Expires:   {_fmt_ts(cred.expires_at)}")
    print(f"  TTL:       {cred.time_remaining():.0f}s remaining")


def cmd_validate(args: argparse.Namespace) -> None:
    from agentiam import AgentIAM
    iam = AgentIAM(default_credential_ttl=args.credential_ttl)
    try:
        cred = iam.validate_credential(args.token)
    except PermissionError as exc:
        print(f"INVALID: {exc}")
        sys.exit(1)
    print(f"VALID — agent: {cred.agent_id}")
    print(f"  Scopes:  {', '.join(cred.scopes) or '(none)'}")
    print(f"  Expires: {_fmt_ts(cred.expires_at)} ({cred.time_remaining():.0f}s remaining)")


def cmd_audit(args: argparse.Namespace) -> None:
    from agentiam import AgentIAM
    iam = AgentIAM(default_credential_ttl=args.credential_ttl)
    events = iam.audit.all()
    if args.agent_id:
        events = [e for e in events if e.agent_id == args.agent_id]
    if not events:
        print("No audit events.")
        return
    for e in events[-args.limit:]:
        ts = _fmt_ts(e.timestamp)
        print(f"[{ts}] {e.agent_id:<28} {e.action:<20} {e.resource:<30} {e.result}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="agentiam", description="AI Agent Identity & Access Management")
    parser.add_argument("--credential-ttl", type=int, default=3600, help="Default credential TTL in seconds")

    sub = parser.add_subparsers(dest="command")

    # register
    p_reg = sub.add_parser("register", help="Register a new agent identity")
    p_reg.add_argument("--name", required=True)
    p_reg.add_argument("--owner", required=True)
    p_reg.add_argument("--description", default="")
    p_reg.add_argument("--model-id", default="")
    p_reg.add_argument("--scopes", nargs="*", default=[])
    p_reg.set_defaults(func=cmd_register)

    # list
    p_list = sub.add_parser("list", help="List registered agents")
    p_list.add_argument("--status", choices=["active", "suspended", "revoked"], default=None)
    p_list.set_defaults(func=cmd_list)

    # issue
    p_issue = sub.add_parser("issue", help="Issue a credential for an agent")
    p_issue.add_argument("--agent-id", required=True)
    p_issue.add_argument("--scopes", nargs="*", default=[])
    p_issue.add_argument("--ttl", type=int, default=None)
    p_issue.set_defaults(func=cmd_issue)

    # validate
    p_val = sub.add_parser("validate", help="Validate a credential token")
    p_val.add_argument("--token", required=True)
    p_val.set_defaults(func=cmd_validate)

    # audit
    p_audit = sub.add_parser("audit", help="Show audit log")
    p_audit.add_argument("--agent-id", default=None)
    p_audit.add_argument("--limit", type=int, default=50)
    p_audit.set_defaults(func=cmd_audit)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
