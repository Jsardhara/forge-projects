"""Compliance report generator — exports audit data in government-ready formats."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Optional

from .models import AccessGrant, AuditEntry, ComplianceReport, ModelTier
from .store import ModelGateStore


def generate_compliance_report(
    store: ModelGateStore,
    since: datetime,
    until: datetime,
) -> ComplianceReport:
    """Generate a compliance report for the given date range."""
    return store.generate_report(since, until)


def export_audit_csv(entries: list[AuditEntry]) -> str:
    """Export audit entries to CSV format."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "audit_id", "employee_email", "model_name", "purpose",
        "accessed_at", "tier_at_access",
    ])
    for entry in entries:
        writer.writerow([
            entry.vid,
            entry.employee_email,
            entry.model_name,
            entry.purpose,
            entry.accessed_at.isoformat(),
            entry.tier_at_access.value,
        ])
    return output.getvalue()


def export_audit_json(entries: list[AuditEntry]) -> str:
    """Export audit entries to JSON format."""
    data = [
        {
            "audit_id": e.vid,
            "employee_email": e.employee_email,
            "model_name": e.model_name,
            "purpose": e.purpose,
            "accessed_at": e.accessed_at.isoformat(),
            "tier_at_access": e.tier_at_access.value,
        }
        for e in entries
    ]
    return json.dumps(data, indent=2)


def export_grants_csv(grants: list[AccessGrant]) -> str:
    """Export access grants to CSV format."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "grant_id", "employee_email", "tier", "justification",
        "approver", "granted_at", "expires_at", "status",
    ])
    for g in grants:
        writer.writerow([
            g.vid,
            g.employee_email,
            g.tier.value,
            g.justification,
            g.approver,
            g.granted_at.isoformat(),
            g.expires_at.isoformat() if g.expires_at else "",
            g.status.value,
        ])
    return output.getvalue()


def format_report_text(report: ComplianceReport) -> str:
    """Format a compliance report as human-readable text."""
    lines = [
        "=" * 60,
        "MODELGATE — COMPLIANCE REPORT",
        "=" * 60,
        f"Period: {report.since.isoformat()} to {report.until.isoformat()}",
        f"Generated: {report.generated_at.isoformat()}",
        "",
        "SUMMARY",
        "-" * 40,
        f"Total model accesses:      {report.total_accesses}",
        f"Unique employees:           {report.unique_employees}",
        f"Classified accesses:        {report.classified_accesses}",
        f"Government-vetted accesses: {report.government_vetted_accesses}",
        "",
        "GRANT STATUS",
        "-" * 40,
        f"Expired grants:             {report.expired_grants}",
        f"Revoked grants:             {report.revoked_grants}",
        f"Pending requests:           {report.pending_requests}",
        "",
        "=" * 60,
    ]
    return "\n".join(lines)
