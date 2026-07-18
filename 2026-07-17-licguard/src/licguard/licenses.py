"""Built-in open-weight model license database.

Terms encoded here reflect publicly known license facts as of mid-2026 and are
intentionally CONSERVATIVE. Canonical license text is always authoritative — LicGuard
prints a reminder to that effect. Models with no published license are represented with
``license=None`` so the engine surfaces them as NEEDS_REVIEW instead of guessing.

Reference points (publicly known):
- Llama 3.1 Community License: standard Apache-2.0-style permissions PLUS an Acceptable
  Use Policy (no certain high-risk/regulated domains) and a license + revenue-share
  obligation once a product using the model reaches >700M monthly users.
- Gemma: Gemma Terms of Use (Apache-2.0-based) with an AUP; redistribution allowed.
- Mistral (e.g. Mistral-7B / Mixtral): Apache-2.0.
- Qwen (e.g. Qwen2.5): Apache-2.0 (some variants carry extra notes).
- DeepSeek (e.g. DeepSeek-V3/R1): MIT.
- Phi (e.g. Phi-3/4): MIT + Microsoft Acceptable Use Policy.
- GLM-4 / ChatGLM: Apache-2.0 (Zhipu AI).
- Kimi (K2 / K3): open-weights under an Apache-2.0-style license (Moonshot AI).
- Inkling: announced open-weights model (2026); license text not yet published -> unknown.
"""

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
    License,
    ModelLicense,
)


def _llama3() -> License:
    return License(
        key="llama3.1-community",
        name="Llama 3.1 Community License",
        spdx=None,
        permissions={PERM_COMMERCIAL, PERM_REDISTRIBUTE, PERM_FINETUNE, PERM_HOSTING},
        conditions={COND_ACCEPTABLE_USE, COND_LICENSE_THRESHOLD},
        limitations=set(),
        max_monthly_users=700_000_000,
        prohibited_uses={
            "unauthorized surveillance",
            "social scoring / surveillance of individuals",
            "exploitation of children",
            "generating disinformation / deceptive political content",
            "fully autonomous weapons / lethal functions",
            "malware / exploits",
            "illegal acts",
        },
        notes="Apache-2.0-style perms + AUP. >700M MAU requires a license and royalty.",
    )


def _gemma() -> License:
    return License(
        key="gemma-terms",
        name="Gemma Terms of Use",
        spdx=None,
        permissions={PERM_COMMERCIAL, PERM_REDISTRIBUTE, PERM_FINETUNE, PERM_HOSTING},
        conditions={COND_ACCEPTABLE_USE},
        limitations=set(),
        prohibited_uses={
            "unauthorized surveillance",
            "exploitation of children",
            "generating disinformation",
            "malware / exploits",
            "illegal acts",
        },
        notes="Apache-2.0-based with an AUP; redistribution allowed with attribution.",
    )


def _apache() -> License:
    return License(
        key="apache-2.0",
        name="Apache License 2.0",
        spdx="Apache-2.0",
        permissions={PERM_COMMERCIAL, PERM_REDISTRIBUTE, PERM_FINETUNE, PERM_HOSTING},
        conditions=set(),
        limitations=set(),
        notes="Permissive. No AUP, no user threshold.",
    )


def _mit() -> License:
    return License(
        key="mit",
        name="MIT License",
        spdx="MIT",
        permissions={PERM_COMMERCIAL, PERM_REDISTRIBUTE, PERM_FINETUNE, PERM_HOSTING},
        conditions=set(),
        limitations=set(),
        notes="Permissive. No AUP, no user threshold.",
    )


def _phi() -> License:
    return License(
        key="mit-ms-aup",
        name="MIT License + Microsoft Acceptable Use Policy",
        spdx="MIT",
        permissions={PERM_COMMERCIAL, PERM_REDISTRIBUTE, PERM_FINETUNE, PERM_HOSTING},
        conditions={COND_ACCEPTABLE_USE},
        limitations=set(),
        prohibited_uses={
            "unauthorized surveillance",
            "exploitation of children",
            "generating disinformation",
            "malware / exploits",
            "illegal acts",
        },
        notes="MIT terms + Microsoft AUP.",
    )


def _unknown() -> None:
    return None


# Canonical model registry. Add new models here.
REGISTRY: dict[str, ModelLicense] = {
    "llama-3.1-8b": ModelLicense(
        "llama-3.1-8b",
        {"llama", "llama3", "llama-3.1", "meta-llama"},
        _llama3(),
    ),
    "llama-3.1-70b": ModelLicense(
        "llama-3.1-70b",
        {"llama", "llama3", "llama-3.1", "meta-llama"},
        _llama3(),
    ),
    "llama-3.1-405b": ModelLicense(
        "llama-3.1-405b",
        {"llama", "llama3", "llama-3.1", "meta-llama"},
        _llama3(),
    ),
    "gemma-2-9b": ModelLicense(
        "gemma-2-9b", {"gemma", "google", "gemma-2"}, _gemma()
    ),
    "gemma-2-27b": ModelLicense(
        "gemma-2-27b", {"gemma", "google", "gemma-2"}, _gemma()
    ),
    "mistral-7b": ModelLicense(
        "mistral-7b", {"mistral"}, _apache()
    ),
    "mixtral-8x7b": ModelLicense(
        "mixtral-8x7b", {"mistral", "mixtral"}, _apache()
    ),
    "qwen2.5-7b": ModelLicense(
        "qwen2.5-7b", {"qwen", "qwen2.5", "alibaba"}, _apache()
    ),
    "qwen2.5-72b": ModelLicense(
        "qwen2.5-72b", {"qwen", "qwen2.5", "alibaba"}, _apache()
    ),
    "deepseek-v3": ModelLicense(
        "deepseek-v3", {"deepseek"}, _mit()
    ),
    "deepseek-r1": ModelLicense(
        "deepseek-r1", {"deepseek"}, _mit()
    ),
    "phi-3-mini": ModelLicense(
        "phi-3-mini", {"phi", "microsoft", "phi-3"}, _phi()
    ),
    "phi-4": ModelLicense(
        "phi-4", {"phi", "microsoft", "phi-4"}, _phi()
    ),
    "glm-4-9b": ModelLicense(
        "glm-4-9b", {"glm", "chatglm", "zhipu"}, _apache()
    ),
    "kimi-k2": ModelLicense(
        "kimi-k2", {"kimi", "moonshot"}, _apache()
    ),
    "kimi-k3": ModelLicense(
        "kimi-k3", {"kimi", "moonshot"}, _apache()
    ),
    "inkling": ModelLicense(
        "inkling",
        {"inkling", "open-weights"},
        _unknown(),
        notes="Open-weights model announced 2026; license text not yet published.",
    ),
}


def resolve_model(model_id: str) -> ModelLicense:
    """Resolve a model id to its record, trying alias/token matching."""
    key = model_id.strip().lower()
    if key in REGISTRY:
        return REGISTRY[key]
    # alias / substring match
    for ml in REGISTRY.values():
        if key in ml.aliases:
            return ml
        if any(tok in key for tok in ml.aliases):
            return ml
    # fallback: best token overlap
    best = None
    best_score = 0
    for ml in REGISTRY.values():
        score = sum(1 for tok in ml.aliases if tok in key)
        if score > best_score:
            best_score = score
            best = ml
    if best is not None and best_score >= 1:
        return best
    return ModelLicense(model_id, set(), None)
