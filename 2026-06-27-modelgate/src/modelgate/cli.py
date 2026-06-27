"""ModelGate CLI — command-line interface for AI model access governance."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from .compliance import (
    export_audit_csv,
    export_audit_json,
    export_grants_csv,
    format_report_text,
    generate_compliance_report,
)
from .models import (
    AccessRequestStatus,
    AccessStatus,
    Model,
    ModelTier,
)
from .policy import PolicyEngine
from .registry import DEFAULT_MODELS
from .store import ModelGateStore


def _get_store(db_path: str | None = None) -> ModelGateStore:
    return ModelGateStore(db_path)


def cmd_init(args: argparse.Namespace) -> None:
    """Initialize ModelGate with default model registry."""
    store = _get_store(args.db)
    count = 0
    for model in DEFAULT_MODELS:
        existing = store.get_model(model.name)
        if existing is None:
            store.register_model(
                name=model.name,
                provider=model.provider,
                tier=model.tier,
                description=model.description,
            )
            count += 1
    store.close()
    print(f"ModelGate initialized. Registered {count} models.")


def cmd_employee_add(args: argparse.Namespace) -> None:
    """Add an employee."""
    store = _get_store(args.db)
    emp = store.add_employee(
        email=args.email,
        name=args.name,
        department=args.department,
    )
    store.close()
    print(f"Employee added: {emp.name} ({emp.email}) — {emp.department}")


def cmd_employee_list(args: argparse.Namespace) -> None:
    """List employees."""
    store = _get_store(args.db)
    employees = store.list_employees()
    store.close()
    if not employees:
        print("No employees registered.")
        return
    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(title="Employees")
        table.add_column("Email", style="cyan")
        table.add_column("Name")
        table.add_column("Department")
        table.add_column("Created")
        for emp in employees:
            table.add_row(emp.email, emp.name, emp.department, emp.created_at.strftime("%Y-%m-%d"))
        console.print(table)
    except ImportError:
        for emp in employees:
            print(f"  {emp.email}  {emp.name}  {emp.department}")


def cmd_models_list(args: argparse.Namespace) -> None:
    """List registered models."""
    store = _get_store(args.db)
    tier = ModelTier(args.tier) if args.tier else None
    models = store.list_models(tier=tier)
    store.close()
    if not models:
        print("No models registered. Run 'modelgate init' first.")
        return
    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(title="Model Registry")
        table.add_column("Model", style="cyan")
        table.add_column("Provider")
        table.add_column("Tier", style="bold")
        table.add_column("Description")
        for m in models:
            tier_style = {
                "public": "green",
                "restricted": "yellow",
                "classified": "red",
                "government_vetted": "bold red",
            }.get(m.tier.value, "")
            table.add_row(m.name, m.provider, f"[{tier_style}]{m.tier.value}[/]", m.description)
        console.print(table)
    except ImportError:
        for m in models:
            print(f"  {m.name}  {m.provider}  {m.tier.value}  {m.description}")


def cmd_access_grant(args: argparse.Namespace) -> None:
    """Grant tier access to an employee."""
    store = _get_store(args.db)
    tier = ModelTier(args.tier)
    policy = PolicyEngine(store)
    error = policy.validate_grant_request(
        employee_email=args.email,
        tier=tier,
        justification=args.justification,
        approver=args.approver,
    )
    if error:
        print(f"ERROR: {error}")
        store.close()
        sys.exit(1)
    grant = store.grant_access(
        employee_email=args.email,
        tier=tier,
        justification=args.justification,
        approver=args.approver,
    )
    store.close()
    print(f"Access granted: {args.email} → {tier.value} (ID: {grant.vid})")


def cmd_access_revoke(args: argparse.Namespace) -> None:
    """Revoke an access grant."""
    store = _get_store(args.db)
    grant = store.revoke_access(args.grant_id)
    store.close()
    if grant:
        print(f"Access revoked: {grant.vid} ({grant.employee_email} → {grant.tier.value})")
    else:
        print(f"Grant not found: {args.grant_id}")


def cmd_access_list(args: argparse.Namespace) -> None:
    """List access grants."""
    store = _get_store(args.db)
    tier = ModelTier(args.tier) if args.tier else None
    status = AccessStatus(args.status) if args.status else None
    grants = store.list_grants(tier=tier, status=status)
    store.close()
    if not grants:
        print("No access grants found.")
        return
    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(title="Access Grants")
        table.add_column("ID", style="cyan")
        table.add_column("Employee")
        table.add_column("Tier", style="bold")
        table.add_column("Approver")
        table.add_column("Granted")
        table.add_column("Expires")
        table.add_column("Status")
        for g in grants:
            status_style = {
                "active": "green",
                "expired": "yellow",
                "revoked": "red",
                "pending": "dim",
            }.get(g.status.value, "")
            table.add_row(
                g.vid,
                g.employee_email,
                g.tier.value,
                g.approver,
                g.granted_at.strftime("%Y-%m-%d"),
                g.expires_at.strftime("%Y-%m-%d") if g.expires_at else "Never",
                f"[{status_style}]{g.status.value}[/]",
            )
        console.print(table)
    except ImportError:
        for g in grants:
            print(f"  {g.vid}  {g.employee_email}  {g.tier.value}  {g.status.value}")


def cmd_access_check(args: argparse.Namespace) -> None:
    """Check if an employee can access a model."""
    store = _get_store(args.db)
    policy = PolicyEngine(store)
    result = policy.check_access(args.email, args.model)
    store.close()
    if result.allowed:
        print(f"ALLOWED: {result.reason}")
    else:
        print(f"DENIED: {result.reason}")


def cmd_request_create(args: argparse.Namespace) -> None:
    """Create an access request."""
    store = _get_store(args.db)
    tier = ModelTier(args.tier)
    req = store.create_request(
        employee_email=args.email,
        tier=tier,
        justification=args.justification,
    )
    store.close()
    print(f"Request created: {req.vid} — {args.email} → {tier.value}")


def cmd_request_approve(args: argparse.Namespace) -> None:
    """Approve an access request."""
    store = _get_store(args.db)
    req = store.approve_request(args.request_id, args.approver)
    if req:
        # Auto-grant access upon approval
        grant = store.grant_access(
            employee_email=req.employee_email,
            tier=req.tier,
            justification=req.justification,
            approver=args.approver,
        )
        print(f"Approved & granted: {req.vid} → {grant.vid} ({req.employee_email} → {req.tier.value})")
    else:
        print(f"Request not found: {args.request_id}")
    store.close()


def cmd_request_deny(args: argparse.Namespace) -> None:
    """Deny an access request."""
    store = _get_store(args.db)
    req = store.deny_request(args.request_id, args.approver, args.reason)
    store.close()
    if req:
        print(f"Denied: {req.vid} — {req.denial_reason}")
    else:
        print(f"Request not found: {args.request_id}")


def cmd_log(args: argparse.Namespace) -> None:
    """Log a model access event."""
    store = _get_store(args.db)
    # Look up model tier
    model = store.get_model(args.model)
    tier = model.tier if model else ModelTier.PUBLIC
    entry = store.log_access(
        employee_email=args.email,
        model_name=args.model,
        purpose=args.purpose,
        tier_at_access=tier,
    )
    store.close()
    print(f"Access logged: {entry.vid} — {args.email} → {args.model} ({tier.value})")


def cmd_report(args: argparse.Namespace) -> None:
    """Generate a compliance report."""
    store = _get_store(args.db)
    since = datetime.fromisoformat(args.since) if args.since else datetime.now(timezone.utc) - timedelta(days=30)
    until = datetime.fromisoformat(args.until) if args.until else datetime.now(timezone.utc)

    report = generate_compliance_report(store, since, until)

    if args.format == "csv":
        entries = store.list_audit(since=since, until=until)
        print(export_audit_csv(entries))
    elif args.format == "json":
        entries = store.list_audit(since=since, until=until)
        print(export_audit_json(entries))
    else:
        print(format_report_text(report))

    store.close()


def cmd_review(args: argparse.Namespace) -> None:
    """Review access — find expired and expiring grants."""
    store = _get_store(args.db)

    # Expire stale grants first
    expired_count = store.expire_stale_grants()

    # Find grants expiring within 7 days
    soon = datetime.now(timezone.utc) + timedelta(days=7)
    all_active = store.list_grants(status=AccessStatus.ACTIVE)
    expiring_soon = [g for g in all_active if g.expires_at and g.expires_at < soon]

    if expired_count:
        print(f"Marked {expired_count} grant(s) as expired.")

    if not expiring_soon:
        print("No grants expiring within 7 days.")
    else:
        try:
            from rich.console import Console
            from rich.table import Table

            console = Console()
            table = Table(title="Grants Expiring Within 7 Days")
            table.add_column("ID", style="cyan")
            table.add_column("Employee")
            table.add_column("Tier")
            table.add_column("Expires")
            for g in expiring_soon:
                table.add_row(
                    g.vid,
                    g.employee_email,
                    g.tier.value,
                    g.expires_at.strftime("%Y-%m-%d %H:%M") if g.expires_at else "N/A",
                )
            console.print(table)
        except ImportError:
            for g in expiring_soon:
                exp = g.expires_at.strftime("%Y-%m-%d") if g.expires_at else "N/A"
                print(f"  {g.vid}  {g.employee_email}  {g.tier.value}  expires: {exp}")

    store.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="modelgate",
        description="ModelGate — AI Model Access Governance",
    )
    parser.add_argument("--db", help="Path to SQLite database", default=None)

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # init
    sub.add_parser("init", help="Initialize with default model registry")

    # employee
    emp = sub.add_parser("employee", help="Employee management")
    emp_sub = emp.add_subparsers(dest="subcommand")
    emp_add = emp_sub.add_parser("add", help="Add employee")
    emp_add.add_argument("--email", required=True)
    emp_add.add_argument("--name", required=True)
    emp_add.add_argument("--department", required=True)
    emp_sub.add_parser("list", help="List employees")

    # models
    models = sub.add_parser("models", help="Model registry")
    models_sub = models.add_subparsers(dest="subcommand")
    ml = models_sub.add_parser("list", help="List models")
    ml.add_argument("--tier", choices=[t.value for t in ModelTier])

    # access
    access = sub.add_parser("access", help="Access management")
    acc_sub = access.add_subparsers(dest="subcommand")

    ag = acc_sub.add_parser("grant", help="Grant tier access")
    ag.add_argument("--email", required=True)
    ag.add_argument("--tier", required=True, choices=[t.value for t in ModelTier])
    ag.add_argument("--justification", required=True)
    ag.add_argument("--approver", required=True)

    ar = acc_sub.add_parser("revoke", help="Revoke access grant")
    ar.add_argument("grant_id")

    al = acc_sub.add_parser("list", help="List access grants")
    al.add_argument("--tier", choices=[t.value for t in ModelTier])
    al.add_argument("--status", choices=[s.value for s in AccessStatus])

    ac = acc_sub.add_parser("check", help="Check if employee can access model")
    ac.add_argument("--email", required=True)
    ac.add_argument("--model", required=True)

    # request
    request = sub.add_parser("request", help="Access request workflow")
    req_sub = request.add_subparsers(dest="subcommand")

    rc = req_sub.add_parser("create", help="Create access request")
    rc.add_argument("--email", required=True)
    rc.add_argument("--tier", required=True, choices=[t.value for t in ModelTier])
    rc.add_argument("--justification", required=True)

    ra = req_sub.add_parser("approve", help="Approve access request")
    ra.add_argument("request_id")
    ra.add_argument("--approver", required=True)

    rd = req_sub.add_parser("deny", help="Deny access request")
    rd.add_argument("request_id")
    rd.add_argument("--approver", required=True)
    rd.add_argument("--reason", default="")

    # log
    log_cmd = sub.add_parser("log", help="Log model access")
    log_cmd.add_argument("--email", required=True)
    log_cmd.add_argument("--model", required=True)
    log_cmd.add_argument("--purpose", required=True)

    # report
    report = sub.add_parser("report", help="Generate compliance report")
    report.add_argument("--since", help="Start date (ISO format)")
    report.add_argument("--until", help="End date (ISO format)")
    report.add_argument("--format", choices=["text", "csv", "json"], default="text")

    # review
    sub.add_parser("review", help="Review expiring grants")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    cmd_map = {
        "init": cmd_init,
        "employee": None,  # handled by subcommand
        "models": None,
        "access": None,
        "request": None,
        "log": cmd_log,
        "report": cmd_report,
        "review": cmd_review,
    }

    # Handle subcommand routing
    if args.command == "employee":
        if args.subcommand == "add":
            cmd_employee_add(args)
        elif args.subcommand == "list":
            cmd_employee_list(args)
        else:
            print("Usage: modelgate employee {add|list}")
        return

    if args.command == "models":
        if args.subcommand == "list":
            cmd_models_list(args)
        else:
            print("Usage: modelgate models list")
        return

    if args.command == "access":
        if args.subcommand == "grant":
            cmd_access_grant(args)
        elif args.subcommand == "revoke":
            cmd_access_revoke(args)
        elif args.subcommand == "list":
            cmd_access_list(args)
        elif args.subcommand == "check":
            cmd_access_check(args)
        else:
            print("Usage: modelgate access {grant|revoke|list|check}")
        return

    if args.command == "request":
        if args.subcommand == "create":
            cmd_request_create(args)
        elif args.subcommand == "approve":
            cmd_request_approve(args)
        elif args.subcommand == "deny":
            cmd_request_deny(args)
        else:
            print("Usage: modelgate request {create|approve|deny}")
        return

    handler = cmd_map.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
