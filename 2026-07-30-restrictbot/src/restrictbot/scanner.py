"""Scanner — match product descriptions against restricted categories."""

import re
from typing import Iterator

from restrictbot.models import (
    Finding,
    RestrictedCategory,
    RestrictionLevel,
    ScanResult,
    Verdict,
)


# The restricted categories from the USG 2026-07-29 ban on foreign-made
# humanoids, robot dogs, and solar inverters.
# Extended with additional plausible categories derived from the same
# national-security rationale.
_RESTRICTED_CATEGORIES: list[RestrictedCategory] = [
    RestrictedCategory(
        slug="humanoid_robot",
        name="Humanoid Robot",
        level=RestrictionLevel.BANNED,
        keywords=("humanoid", "humanoid robot", "bipedal robot", "human-like robot",
                  "android robot", "human-shaped robot"),
        description="New foreign-made humanoid robots (banned for national security)",
    ),
    RestrictedCategory(
        slug="robot_dog",
        name="Robot Dog / Quadruped",
        level=RestrictionLevel.BANNED,
        keywords=("robot dog", "quadruped robot", "robotic dog", "robot quadruped",
                  "autonomous quadruped", "military robot dog", "biomimetic quadruped"),
        description="New foreign-made robot dogs / biomimetic quadrupeds (banned for national security)",
    ),
    RestrictedCategory(
        slug="solar_inverter",
        name="Solar Inverter",
        level=RestrictionLevel.BANNED,
        keywords=("solar inverter", "photovoltaic inverter", "PV inverter",
                  "string inverter", "solar power inverter"),
        description="New foreign-made solar inverters (banned for national security)",
    ),
    RestrictedCategory(
        slug="humanoid_upper_torso",
        name="Humanoid Upper Torso / Telepresence",
        level=RestrictionLevel.RESTRICTED,
        keywords=("telepresence robot", "remote presence robot", "humanoid torso",
                  "humanoid upper body", "robotic torso"),
        description="Foreign-made humanoid upper-torso/telepresence systems (restricted, special permit required)",
    ),
    RestrictedCategory(
        slug="biomimetic_robot",
        name="Biomimetic Robot",
        level=RestrictionLevel.RESTRICTED,
        keywords=("biomimetic robot", "bio-inspired robot", "snake robot",
                  "legged robot", "hexapod robot", "octopus robot"),
        description="Foreign-made biomimetic robots (restricted, special permit required)",
    ),
    RestrictedCategory(
        slug="exoskeleton",
        name="Powered Exoskeleton",
        level=RestrictionLevel.MONITORED,
        keywords=("exoskeleton", "powered exoskeleton", "wearable robot",
                  "assistive exoskeleton", "military exoskeleton"),
        description="Foreign-made powered exoskeletons (monitored, import declaration required)",
    ),
    RestrictedCategory(
        slug="autonomous_ground_vehicle",
        name="Autonomous Ground Vehicle (Small)",
        level=RestrictionLevel.MONITORED,
        keywords=("autonomous ground vehicle", "unmanned ground vehicle", "UGV",
                  "robotic mule", "autonomous mule", "pack robot"),
        description="Foreign-made small autonomous ground vehicles (monitored, import declaration required)",
    ),
]


def _build_patterns() -> list[tuple[RestrictedCategory, re.Pattern]]:
    """Build regex patterns for each category."""
    results = []
    for cat in _RESTRICTED_CATEGORIES:
        pattern = re.compile(
            r"\b(?:" + "|".join(re.escape(kw) for kw in cat.keywords) + r")\b",
            re.IGNORECASE,
        )
        results.append((cat, pattern))
    return results


_PATTERNS = _build_patterns()


def scan_product(name: str, description: str) -> ScanResult:
    """Scan a product description against all restricted categories.

    Returns a ScanResult with findings and overall verdict.
    """
    text = f"{name} {description}".lower()
    findings: list[Finding] = []

    for cat, pattern in _PATTERNS:
        matches = pattern.findall(text)
        if matches:
            match_str = matches[0] if len(matches) == 1 else f"{matches[0]} (+{len(matches)-1} more)"
            if cat.level == RestrictionLevel.BANNED:
                verdict = Verdict.FAIL
                reason = f"BANNED: {cat.name} — {cat.description}"
            elif cat.level == RestrictionLevel.RESTRICTED:
                verdict = Verdict.WARN
                reason = f"RESTRICTED: {cat.name} — {cat.description}"
            else:
                verdict = Verdict.WARN
                reason = f"MONITORED: {cat.name} — {cat.description}"

            findings.append(Finding(
                category=cat.slug,
                verdict=verdict,
                reason=reason,
                match=match_str,
            ))

    # Compute overall verdict
    if any(f.verdict == Verdict.FAIL for f in findings):
        overall = Verdict.FAIL
    elif any(f.verdict == Verdict.WARN for f in findings):
        overall = Verdict.WARN
    else:
        overall = Verdict.PASS

    # Score: 0.0 = safe, 1.0 = highly restricted
    score = 0.0
    for f in findings:
        if f.verdict == Verdict.FAIL:
            score = max(score, 1.0)
        elif f.verdict == Verdict.WARN:
            score = max(score, 0.6)

    return ScanResult(
        product_name=name,
        description=description,
        verdict=overall,
        findings=findings,
        score=score,
    )


def scan_products(products: list[tuple[str, str]]) -> list[ScanResult]:
    """Scan multiple products. Returns list of results."""
    return [scan_product(name, desc) for name, desc in products]


def available_categories() -> list[RestrictedCategory]:
    """Return the list of restricted categories being checked."""
    return list(_RESTRICTED_CATEGORIES)