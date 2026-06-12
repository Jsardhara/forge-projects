"""Guardrail detection — probe models and detect invisible throttling."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

from agentwatch.db import (
    get_db,
    get_guardrail_probe,
    record_guardrail_result,
    create_alert,
    get_guardrail_results,
)


@dataclass
class ProbeResult:
    probe_id: str
    passed: bool
    drift_score: float
    keywords_found: list[str]
    keywords_missing: list[str]
    response_text: str
    checked_at: float


def run_probe(conn, probe_id: str, call_model_fn=None) -> ProbeResult:
    """Run a guardrail probe against a model.

    Args:
        conn: Database connection
        probe_id: The probe to run
        call_model_fn: Callable(prompt: str) -> str. If None, returns a simulated response.
    """
    probe = get_guardrail_probe(conn, probe_id)
    if not probe:
        raise ValueError(f"Probe {probe_id} not found")

    prompt = probe["prompt"]
    expected = json.loads(probe["expected_keywords"])

    # Get call model function
    if call_model_fn is None:
        response = _simulate_model_call(prompt, probe["provider"], probe["model"])
    else:
        response = call_model_fn(prompt)

    # Check for expected keywords
    response_lower = response.lower()
    found = [kw for kw in expected if kw.lower() in response_lower]
    missing = [kw for kw in expected if kw.lower() not in response_lower]

    # Calculate drift score (0.0 = no drift, 1.0 = complete drift)
    drift_score = len(missing) / max(len(expected), 1) if expected else 0.0

    # A probe passes if drift is below 50%
    passed = drift_score < 0.5

    result = ProbeResult(
        probe_id=probe_id,
        passed=passed,
        drift_score=round(drift_score, 3),
        keywords_found=found,
        keywords_missing=missing,
        response_text=response[:500],  # Truncate for storage
        checked_at=time.time(),
    )

    # Store result
    record_guardrail_result(
        conn,
        probe_id=probe_id,
        response_text=result.response_text,
        keywords_found=json.dumps(found),
        keywords_missing=json.dumps(missing),
        drift_score=result.drift_score,
        passed=result.passed,
    )

    # Check for drift trend — compare with recent results
    recent = get_guardrail_results(conn, probe_id, limit=5)
    if len(recent) >= 3:
        recent_drift = [r["drift_score"] for r in recent[:3]]
        avg_drift = sum(recent_drift) / len(recent_drift)
        if avg_drift > 0.3:
            create_alert(
                conn,
                alert_type="guardrail_drift",
                probe_id=probe_id,
                message=f"Guardrail drift detected for probe '{probe['name']}': avg drift={avg_drift:.2f} over last 3 checks",
                severity="alert" if avg_drift > 0.5 else "warn",
            )

    if not passed:
        create_alert(
            conn,
            alert_type="guardrail_failed",
            probe_id=probe_id,
            message=f"Guardrail probe '{probe['name']}' FAILED: missing keywords={missing}",
            severity="alert",
        )

    return result


def _simulate_model_call(prompt: str, provider: str, model: str) -> str:
    """Simulate a model response for testing without API keys.

    Returns a reasonable response that includes common keywords so probes pass by default.
    """
    return (
        f"This is a simulated response from {provider}/{model}. "
        "The model is functioning normally and provides accurate, helpful responses. "
        "Python is a versatile programming language. "
        "Machine learning and artificial intelligence are transforming technology. "
        "The answer is comprehensive and well-structured."
    )


def get_drift_trend(conn, probe_id: str, window: int = 10) -> list[dict]:
    """Get drift trend data for a probe."""
    results = get_guardrail_results(conn, probe_id, limit=window)
    return [
        {
            "drift_score": r["drift_score"],
            "passed": bool(r["passed"]),
            "checked_at": r["checked_at"],
        }
        for r in reversed(results)
    ]
