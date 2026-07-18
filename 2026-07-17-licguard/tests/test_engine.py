import json
import os
import tempfile

from licguard.engine import evaluate, evaluate_manifest
from licguard.models import DeploymentContext, Verdict
from licguard.licenses import REGISTRY, resolve_model


def test_known_license_count():
    # We ship a non-trivial offline database.
    assert len(REGISTRY) >= 15


def test_permissive_commercial_ok():
    v = evaluate("mistral-7b", DeploymentContext(commercial=True))
    assert v.status == "COMPLIANT", v.reasons
    assert v.license_key == "apache-2.0"


def test_permissive_redistribute_ok():
    v = evaluate("deepseek-v3", DeploymentContext(redistribute=True, commercial=True))
    assert v.status == "COMPLIANT", v.reasons


def test_phi_aup_clean_ok():
    v = evaluate("phi-3-mini", DeploymentContext(commercial=True, use_case="customer support chatbot"))
    assert v.status == "COMPLIANT", v.reasons


def test_llama_commercial_under_threshold_ok():
    v = evaluate("llama-3.1-8b", DeploymentContext(commercial=True, monthly_active_users=10_000_000))
    assert v.status == "COMPLIANT", v.reasons


def test_llama_commercial_over_threshold_noncompliant():
    v = evaluate(
        "llama-3.1-8b",
        DeploymentContext(commercial=True, monthly_active_users=1_000_000_000),
    )
    assert v.status == "NON_COMPLIANT", v.reasons
    assert any("threshold" in r.lower() or "700" in r for r in v.reasons)


def test_llama_aup_breach_noncompliant():
    v = evaluate(
        "llama-3.1-8b",
        DeploymentContext(commercial=True, use_case="build malware and exploits for clients"),
    )
    assert v.status == "NON_COMPLIANT", v.reasons
    assert any("prohibited" in r.lower() for r in v.reasons)


def test_negation_filter_no_false_positive():
    # "not malware" must NOT trip the AUP.
    v = evaluate(
        "llama-3.1-8b",
        DeploymentContext(commercial=True, use_case="we do NOT build malware; we build a journaling app"),
    )
    assert v.status == "COMPLIANT", v.reasons


def test_unknown_model_needs_review():
    v = evaluate("inkling", DeploymentContext(commercial=True))
    assert v.status == "NEEDS_REVIEW", v.reasons
    assert v.license_key is None


def test_unknown_model_id_needs_review():
    v = evaluate("some-brand-new-model-xyz", DeploymentContext(commercial=True))
    assert v.status == "NEEDS_REVIEW", v.reasons


def test_alias_resolution():
    # "llama" should resolve to a Llama license record.
    ml = resolve_model("llama")
    assert ml.license is not None
    assert ml.license.key == "llama3.1-community"


def test_manifest_scan_mixed():
    manifest = {
        "models": [
            {"model": "mistral-7b", "use": {"commercial": True}},
            {
                "model": "llama-3.1-70b",
                "use": {"commercial": True, "monthly_active_users": 2_000_000_000},
            },
            {"model": "inkling", "use": {"commercial": True}},
        ]
    }
    vs = evaluate_manifest(manifest)
    assert len(vs) == 3
    statuses = {v.model_id: v.status for v in vs}
    assert statuses["mistral-7b"] == "COMPLIANT"
    assert statuses["llama-3.1-70b"] == "NON_COMPLIANT"
    assert statuses["inkling"] == "NEEDS_REVIEW"


def test_verdict_merge_downgrades():
    a = Verdict("COMPLIANT", "m", "apache-2.0", ["ok"], 1.0)
    b = Verdict("NON_COMPLIANT", "m", "apache-2.0", ["bad"], 1.0)
    merged = a.merge(b)
    assert merged.status == "NON_COMPLIANT"
    assert "ok" in merged.reasons and "bad" in merged.reasons
