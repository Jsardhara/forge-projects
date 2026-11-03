"""Run one verifier in its own subprocess, bounded, and never store its output."""

import os
import subprocess
import sys
import time
from typing import Dict, Optional

from .discover import Verifier
from .models import CLEAN, ERROR, FINDINGS, UNMEASURABLE, VerifierResult, status_for_exit
from .specs import volatile_for
from .state import signal_digest

TRACEBACK = "Traceback (most recent call last)"


def _child_env(src_dir: str, extra: Optional[Dict[str, str]]) -> Dict[str, str]:
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)  # never let the parent's import path leak in
    for key, value in (extra or {}).items():
        if key != "PYTHONPATH":
            env[str(key)] = str(value)
    env["PYTHONPATH"] = src_dir
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    return env


def run_verifier(
    verifier: Verifier,
    env: Optional[Dict[str, str]] = None,
    timeout: float = 120.0,
    args: Optional[tuple] = None,
) -> VerifierResult:
    """Execute `<python> -m <module> [args]` and classify the outcome.

    Classification is deliberately conservative:
      * a traceback is `error`, whatever the exit code says;
      * exit 0 with no output at all is `unmeasurable` — nothing was proven;
      * anything outside 0/1/2 is `error`.
    """
    cmd = [sys.executable, "-m", verifier.spec.module, *(args or ())]
    started = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            cwd=verifier.spec_path,
            env=_child_env(verifier.src_dir, env),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - started
        return VerifierResult(
            name=verifier.name,
            status=ERROR,
            exit_code=None,
            duration_s=elapsed,
            digest="",
            error=f"timeout after {timeout:g}s",
        )
    except OSError as exc:
        elapsed = time.monotonic() - started
        return VerifierResult(
            name=verifier.name,
            status=ERROR,
            exit_code=None,
            duration_s=elapsed,
            digest="",
            error=f"could not launch: {exc}",
        )

    elapsed = time.monotonic() - started
    out = proc.stdout or ""
    err = proc.stderr or ""
    digest = signal_digest(out, extra=volatile_for(verifier.name))

    if TRACEBACK in err or TRACEBACK in out:
        return VerifierResult(
            name=verifier.name,
            status=ERROR,
            exit_code=proc.returncode,
            duration_s=elapsed,
            digest=digest,
            error="crashed: Traceback (most recent call last) in verifier output",
        )

    status = status_for_exit(proc.returncode)
    if status == FINDINGS and not out.strip():
        # Exit 1 with an empty stdout is how a broken interpreter/module launch
        # looks. A verifier that genuinely found something always says what.
        return VerifierResult(
            name=verifier.name,
            status=ERROR,
            exit_code=proc.returncode,
            duration_s=elapsed,
            digest=digest,
            error="exited 1 with no output — treated as broken, not as a finding",
        )
    if status == CLEAN and not out.strip() and not err.strip():
        return VerifierResult(
            name=verifier.name,
            status=UNMEASURABLE,
            exit_code=proc.returncode,
            duration_s=elapsed,
            digest=digest,
            error="no output — nothing was proven",
        )

    error = None
    if status == ERROR:
        tail = (err.strip() or out.strip()).splitlines()[-1:] or [""]
        error = f"unexpected exit {proc.returncode}: {tail[0][:200]}"
    elif status == UNMEASURABLE:
        error = "verifier reported it could not measure"

    return VerifierResult(
        name=verifier.name,
        status=status,
        exit_code=proc.returncode,
        duration_s=elapsed,
        digest=digest,
        error=error,
    )
