"""EduGate — AI Access Gateway for Schools."""

from edugate.policy import PolicyEngine, AccessDecision
from edugate.audit import AuditLogger
from edugate.compliance import ComplianceReport
from edugate.gateway import Gateway

__all__ = [
    "PolicyEngine",
    "AccessDecision",
    "AuditLogger",
    "ComplianceReport",
    "Gateway",
]
