"""AgentVault command-line interface.

Subcommands:
  demo     Run an end-to-end demonstration of the secret-scoped flow.
  secret   add / delete / list real secrets in the vault.
  session  issue / revoke / list scoped agent sessions.
  egress   set / add / check egress allowlist rules.
  audit    verify + print the tamper-evident access log.
"""
from __future__ import annotations

import argparse
import sys
from datetime import timedelta

from agentvault import (
    AuditTrail,
    EgressFilter,
    EgressRule,
    Scope,
    SecretKind,
    Session,
    Vault,
    VaultConfig,
)
from agentvault.models import SecretKind as _SK


def _build_vault() -> Vault:
    return Vault(VaultConfig())


def _cmd_demo(args: argparse.Namespace) -> int:
    v = _build_vault()
    # 1. Store a real secret (e.g. an Alpaca API key) -- agent never sees this raw.
    key = v.add_secret(
        "alpaca-key", "REAL_SECRET_VALUE_DO_NOT_LEAK", kind=SecretKind.API_KEY,
        allowed_hosts=("api.alpaca.markets",),
    )
    # 2. Issue a scoped, short-lived session that may ONLY use this secret.
    sess = v.issue_session(
        scope=Scope(secret_ids=(key.sid,), allowed_hosts=("api.alpaca.markets",),
                    can_proxy_egress=True, max_uses=5),
        ttl=timedelta(minutes=15),
    )
    print(f"[vault] stored secret {key.sid}")
    print(f"[vault] issued session {sess.session_id} (TTL 15m, max 5 uses)")

    # 3. Agent resolves the secret -> allowed.
    val = v.resolve(sess.session_id, key.sid)
    print(f"[agent] resolved secret -> {val}")

    # 4. Agent tries a host NOT on the allowlist -> denied.
    try:
        v.check_egress(sess.session_id, "evil.example.com", 443)
        print("[agent] egress ALLOWED (unexpected)")
    except Exception as e:  # noqa: BLE001
        print(f"[agent] egress BLOCKED -> {e}")

    # 5. Operator revokes the session -> further resolves denied.
    v.revoke_session(sess.session_id)
    try:
        v.resolve(sess.session_id, key.sid)
        print("[agent] resolve after revoke ALLOWED (unexpected)")
    except Exception as e:  # noqa: BLE001
        print(f"[agent] resolve after revoke BLOCKED -> {e}")

    # 6. Tamper-evident audit proof.
    print(f"[audit] chain intact: {v.audit_verify()}")
    print(f"[audit] {len(v.audit_trail)} entries recorded")
    return 0


def _cmd_secret(args: argparse.Namespace) -> int:
    v = _build_vault()
    if args.secret_cmd == "add":
        kind = SecretKind(args.kind)
        s = v.add_secret(args.name, args.value, kind=kind, allowed_hosts=tuple(args.host or []))
        print(f"added secret {s.sid} ({s.name})")
        return 0
    if args.secret_cmd == "delete":
        v.delete_secret(args.sid)
        print(f"deleted secret {args.sid}")
        return 0
    if args.secret_cmd == "list":
        for s in v.secrets:
            print(f"{s.sid}\t{s.name}\t{s.kind.value}\thosts={list(s.allowed_hosts)}")
        return 0
    return 1


def _cmd_session(args: argparse.Namespace) -> int:
    v = _build_vault()
    if args.session_cmd == "issue":
        ttl = timedelta(minutes=args.ttl) if args.ttl else None
        scope = Scope(
            secret_ids=tuple(args.secret or []),
            allowed_hosts=tuple(args.host or []),
            can_proxy_egress=args.egress,
            max_uses=args.max_uses,
        )
        s = v.issue_session(scope=scope, ttl=ttl)
        print(f"issued {s.session_id}  expires={s.expires_at}  egress={scope.can_proxy_egress}")
        return 0
    if args.session_cmd == "revoke":
        v.revoke_session(args.sid)
        print(f"revoked {args.sid}")
        return 0
    if args.session_cmd == "list":
        for s in v.sessions:
            print(f"{s.session_id}\tuses={s.use_count}\trevoked={s.revoked}\texpired={s.is_expired()}")
        return 0
    return 1


def _cmd_egress(args: argparse.Namespace) -> int:
    f = EgressFilter()
    if args.egress_cmd == "check":
        if args.rules:
            for r in args.rules:
                f.add_rule(r)
        ok = f.allow(args.host, args.port)
        print(f"{'ALLOW' if ok else 'DENY'} {args.host}" + (f":{args.port}" if args.port else ""))
        return 0 if ok else 2
    if args.egress_cmd == "add":
        for r in args.rules:
            f.add_rule(r)
        for r in f.rules:
            print(f"rule {r.pattern} ports={list(r.ports)}")
        return 0
    return 1


def _cmd_audit(args: argparse.Namespace) -> int:
    t = AuditTrail()
    # No live vault here; the demo/run command is the real source. Just show verify
    # on an empty trail is True.
    print(f"empty trail verify: {t.verify()}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="agentvault", description="Secret-scoped execution layer for AI agents.")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("demo", help="End-to-end demonstration").set_defaults(func=_cmd_demo)

    sp = sub.add_parser("secret", help="Manage vault secrets")
    ss = sp.add_subparsers(dest="secret_cmd", required=True)
    a = ss.add_parser("add"); a.add_argument("--name", required=True); a.add_argument("--value", required=True)
    a.add_argument("--kind", default="generic", choices=[k.value for k in SecretKind])
    a.add_argument("--host", action="append", help="allowed host (repeatable)")
    a.set_defaults(func=_cmd_secret)
    d = ss.add_parser("delete"); d.add_argument("--sid", required=True); d.set_defaults(func=_cmd_secret)
    ss.add_parser("list").set_defaults(func=_cmd_secret)

    sp2 = sub.add_parser("session", help="Manage agent sessions")
    ss2 = sp2.add_subparsers(dest="session_cmd", required=True)
    i = ss2.add_parser("issue"); i.add_argument("--secret", action="append"); i.add_argument("--host", action="append")
    i.add_argument("--egress", action="store_true"); i.add_argument("--ttl", type=int, default=0)
    i.add_argument("--max-uses", type=int, default=None); i.set_defaults(func=_cmd_session)
    r = ss2.add_parser("revoke"); r.add_argument("--sid", required=True); r.set_defaults(func=_cmd_session)
    ss2.add_parser("list").set_defaults(func=_cmd_session)

    ep = sub.add_parser("egress", help="Egress allowlist")
    es = ep.add_subparsers(dest="egress_cmd", required=True)
    ec = es.add_parser("check"); ec.add_argument("--host", required=True); ec.add_argument("--port", type=int, default=None)
    ec.add_argument("--rules", action="append", help="allow rule (repeatable)"); ec.set_defaults(func=_cmd_egress)
    ea = es.add_parser("add"); ea.add_argument("--rules", nargs="+", required=True); ea.set_defaults(func=_cmd_egress)

    sub.add_parser("audit", help="Audit trail helpers").set_defaults(func=_cmd_audit)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
