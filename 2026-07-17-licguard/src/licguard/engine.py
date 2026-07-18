"""LicGuard compliance engine.

Offline, deterministic evaluation of whether a deployment context is permissible under
a model's license terms.
"""

import re

from licguard.models import (
    COND_ACCEPTABLE_USE,
    COND_LICENSE_THRESHOLD,
    LIM_COMMERCIAL,
    LIM_FINETUNE,
    LIM_REDISTRIBUTE,
    PERM_COMMERCIAL,
    PERM_FINETUNE,
    PERM_HOSTING,
    PERM_REDISTRIBUTE,
    DeploymentContext,
    License,
    ModelLicense,
    Verdict,
)
from licguard.licenses import resolve_model

# Negation filter: avoid flagging a banned-domain mention that is explicitly negated.
# Only a negative word IMMEDIATELY followed by the prohibited phrase (or a short
# stopword) counts as a negation. This prevents false matches like the "nt" in
# "clients" being read as "not".
_NEGATION_RE = re.compile(
    r"\b(no|not|without|never|non-)\b[\s\w]{0,15}?(malware|exploit|weapon|surveillance|"
    r"disinformation|children|illegal)\b",
    re.IGNORECASE,
)


def _mentions_prohibited(use_case: str, prohibited: set) -> list:
    """Return the subset of prohibited-use phrases present in the free-text use case.

    Each stored phrase may bundle synonyms (e.g. "malware / exploits"). We match on any
    individual token, then report the canonical phrase. Applies negation filtering so
    that "not malware" does not trigger a false positive.
    """
    text = (use_case or "").lower()
    hits = []
    for phrase in prohibited:
        tokens = [t.strip() for t in phrase.lower().split("/") if t.strip()]
        if any(tok in text for tok in tokens) and not _NEGATION_RE.search(text):
            hits.append(phrase)
    return hits


def evaluate(model_id: str, ctx: DeploymentContext) -> Verdict:
    """Evaluate a model + deployment context into a verdict."""
    ml = resolve_model(model_id)
    model_resolved_id = ml.model_id

    if ml.license is None:
        return Verdict(
            status="NEEDS_REVIEW",
            model_id=model_resolved_id,
            license_key=None,
            reasons=[
                "No published license on file for this model. Verify the canonical "
                "license text before deploying.",
                ml.notes or "Treat as unreviewed until license is confirmed.",
            ],
            confidence=0.4,
        )

    lic: License = ml.license
    reasons: list = []

    # 1. Permission checks (only meaningful when the action is requested)
    if ctx.commercial and LIM_COMMERCIAL in lic.limitations:
        reasons.append("License forbids commercial use but deployment is commercial.")
    if ctx.redistribute and LIM_REDISTRIBUTE in lic.limitations:
        reasons.append("License forbids redistribution but redistribution is intended.")
    if ctx.finetune and LIM_FINETUNE in lic.limitations:
        reasons.append("License forbids fine-tuning but fine-tuning is intended.")
    if ctx.hosting and PERM_HOSTING not in lic.permissions:
        reasons.append("License does not grant hosting / third-party inference rights.")

    # 2. Acceptable-use policy scan (only if there is free-text use case)
    if COND_ACCEPTABLE_USE in lic.conditions and ctx.use_case:
        hits = _mentions_prohibited(ctx.use_case, lic.prohibited_uses)
        for h in hits:
            reasons.append(f"Use case mentions a prohibited domain: '{h}' (AUP breach).")

    # 3. Commercial user-threshold (Llama >700M MAU clause)
    if (
        COND_LICENSE_THRESHOLD in lic.conditions
        and lic.max_monthly_users is not None
        and ctx.commercial
        and ctx.monthly_active_users is not None
        and ctx.monthly_active_users > lic.max_monthly_users
    ):
        reasons.append(
            f"Monthly active users ({ctx.monthly_active_users:,}) exceed the "
            f"{lic.max_monthly_users:,} threshold -> a direct license + royalty is required."
        )

    # Decide status
    if reasons:
        status = "NON_COMPLIANT"
        confidence = 0.9
    else:
        status = "COMPLIANT"
        confidence = 0.9
        reasons.append("Intended use is within the encoded license terms.")

    return Verdict(
        status=status,
        model_id=model_resolved_id,
        license_key=lic.key,
        reasons=reasons,
        confidence=confidence,
    )


def evaluate_manifest(manifest: dict) -> list:
    """Evaluate every entry in a deployment manifest.

    Manifest shape: {"models": [{"model": "...", "use": {...DeploymentContext fields...}}]}
    """
    out = []
    for entry in manifest.get("models", []):
        mid = entry.get("model", "")
        use = entry.get("use", {})
        ctx = DeploymentContext(
            commercial=bool(use.get("commercial", False)),
            redistribute=bool(use.get("redistribute", False)),
            finetune=bool(use.get("finetune", False)),
            hosting=bool(use.get("hosting", False)),
            monthly_active_users=use.get("monthly_active_users"),
            use_case=use.get("use_case", ""),
        )
        out.append(evaluate(mid, ctx))
    return out
