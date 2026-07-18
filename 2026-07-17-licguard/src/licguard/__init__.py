"""LicGuard — offline ML/AI open-weight model license compliance checker."""

from licguard.models import (
    DeploymentContext,
    License,
    ModelLicense,
    Verdict,
)
from licguard.engine import evaluate, evaluate_manifest
from licguard.licenses import REGISTRY, resolve_model

__all__ = [
    "DeploymentContext",
    "License",
    "ModelLicense",
    "Verdict",
    "evaluate",
    "evaluate_manifest",
    "REGISTRY",
    "resolve_model",
]
