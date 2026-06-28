"""Patch suggestion generator for detected 0-day vulnerabilities."""

from __future__ import annotations

from datetime import datetime, timezone

from zerosentinel.models import (
    PatchSuggestion,
    Severity,
    VulnerabilityFingerprint,
)

# Patch templates by vulnerability type
_PATCH_TEMPLATES: dict[str, dict[str, str]] = {
    "rce": {
        "fix": "Upgrade {product} to the latest stable version. Apply vendor patch immediately.",
        "workaround": "Disable affected feature/module. Restrict network access to {product} endpoints.",
        "type": "version_pin",
    },
    "xss": {
        "fix": "Update {product} and apply output encoding. Sanitize all user inputs.",
        "workaround": "Enable Content-Security-Policy headers. Implement X-XSS-Protection.",
        "type": "code_fix",
    },
    "sql_injection": {
        "fix": "Update {product} and migrate to parameterized queries/prepared statements.",
        "workaround": "Enable WAF SQL injection rules. Restrict DB user permissions.",
        "type": "code_fix",
    },
    "authentication_bypass": {
        "fix": "Apply vendor authentication patch. Rotate all credentials immediately.",
        "workaround": "Enable MFA. Restrict access to authentication endpoints by IP.",
        "type": "config_change",
    },
    "privilege_escalation": {
        "fix": "Update {product} to patched version. Review and harden privilege boundaries.",
        "workaround": "Run {product} with minimal required privileges. Enable SELinux/AppArmor.",
        "type": "version_pin",
    },
    "buffer_overflow": {
        "fix": "Update {product} to patched version with ASLR/DEP enabled.",
        "workaround": "Enable stack canaries and ASLR. Restrict input buffer sizes.",
        "type": "version_pin",
    },
    "directory_traversal": {
        "fix": "Update {product} and validate all file path inputs against allowlists.",
        "workaround": "Chroot jail for file operations. Disable symbolic link following.",
        "type": "code_fix",
    },
    "ssrf": {
        "fix": "Update {product} and implement URL allowlisting for outbound requests.",
        "workaround": "Block outbound traffic to internal IP ranges. Disable URL fetching.",
        "type": "config_change",
    },
    "deserialization": {
        "fix": "Update {product} and replace native deserialization with safe data formats (JSON).",
        "workaround": "Disable deserialization of untrusted data. Implement type allowlists.",
        "type": "code_fix",
    },
    "race_condition": {
        "fix": "Update {product} and implement proper locking/synchronization.",
        "workaround": "Enable serialization for critical operations. Add retry logic.",
        "type": "code_fix",
    },
    "use_after_free": {
        "fix": "Update {product} to patched version with memory safety fixes.",
        "workaround": "Enable heap hardening (safe-unlink, ASAN in testing).",
        "type": "version_pin",
    },
    "supply_chain": {
        "fix": "Pin dependency versions with hash verification. Audit dependency tree.",
        "workaround": "Enable lockfile strict mode. Use private registry with allowlist.",
        "type": "config_change",
    },
    "memory_corruption": {
        "fix": "Update {product} immediately. Enable all memory safety mitigations.",
        "workaround": "Enable ASLR, DEP/NX, CFG, ACG. Reduce attack surface.",
        "type": "version_pin",
    },
    "sandbox_escape": {
        "fix": "Update {product} and apply container/sandbox hardening patches.",
        "workaround": "Use gVisor/Firecracker. Drop all capabilities. Enable seccomp.",
        "type": "config_change",
    },
    "kernel": {
        "fix": "Update kernel to latest stable version. Apply all security patches.",
        "workaround": "Enable kernel lockdown mode. Restrict module loading.",
        "type": "version_pin",
    },
    "unknown": {
        "fix": "Review {product} for patches. Apply vendor security advisory.",
        "workaround": "Isolate {product} in restricted network segment.",
        "type": "workaround",
    },
}

# Severity-based confidence multipliers
_SEVERITY_CONFIDENCE = {
    Severity.CRITICAL: 0.95,
    Severity.HIGH: 0.85,
    Severity.MEDIUM: 0.70,
    Severity.LOW: 0.50,
}


class PatchGenerator:
    """Generates patch suggestions for detected vulnerabilities."""

    def generate(
        self,
        fingerprint: VulnerabilityFingerprint,
    ) -> PatchSuggestion:
        """Generate a patch suggestion for a vulnerability fingerprint."""
        vuln_type = fingerprint.vulnerability_type
        product = fingerprint.affected_product

        template = _PATCH_TEMPLATES.get(vuln_type, _PATCH_TEMPLATES["unknown"])

        fix = template["fix"].format(product=product)
        patch_type = template["type"]

        # Calculate confidence based on severity and data quality
        base_confidence = _SEVERITY_CONFIDENCE.get(fingerprint.severity, 0.5)

        # Boost confidence if we have CVE ID
        if fingerprint.cve_id:
            base_confidence = min(1.0, base_confidence + 0.05)

        # Boost confidence if we have specific versions
        if fingerprint.affected_versions:
            base_confidence = min(1.0, base_confidence + 0.05)

        # Determine effort
        effort = self._estimate_effort(fingerprint)

        return PatchSuggestion(
            fingerprint=fingerprint,
            confidence=round(base_confidence, 2),
            suggested_fix=fix,
            patch_type=patch_type,
            references=fingerprint.references,
            estimated_effort=effort,
        )

    def generate_batch(
        self,
        fingerprints: list[VulnerabilityFingerprint],
    ) -> list[PatchSuggestion]:
        """Generate patch suggestions for multiple fingerprints."""
        return [self.generate(fp) for fp in fingerprints]

    def _estimate_effort(self, fingerprint: VulnerabilityFingerprint) -> str:
        """Estimate remediation effort."""
        if fingerprint.severity == Severity.CRITICAL:
            if fingerprint.vulnerability_type in ("rce", "kernel", "sandbox_escape"):
                return "high"
            return "medium"
        if fingerprint.severity == Severity.HIGH:
            return "medium"
        return "low"
