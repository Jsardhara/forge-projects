"""Text rendering and the fail-closed exit contract."""

from .ledger import (
    capability_counts,
    divergence,
    frontmatter_problems,
    root_counts,
    script_count,
    skill_capability_counts,
    skill_counts,
    top_skills,
)
from .models import CAPABILITIES, CAPABILITY_HELP

EXIT_CLEAN = 0
EXIT_FINDING = 1
EXIT_UNMEASURABLE = 2

MAX_LISTED = 12


def _plural(count, noun):
    return "%d %s%s" % (count, noun, "" if count == 1 else "s")


def _section(title):
    return ["", title]


def _capabilities_block(ledger):
    lines = _section("CAPABILITIES (static, from script bodies)")
    per_script = capability_counts(ledger)
    per_skill = skill_capability_counts(ledger)
    for cap in CAPABILITIES:
        lines.append(
            "  %-16s %4d script(s) %4d skill(s)   %s"
            % (cap, per_script.get(cap, 0), per_skill.get(cap, 0), CAPABILITY_HELP.get(cap, ""))
        )
    return lines


def _roots_block(ledger):
    lines = _section("ROOTS")
    for label, skills, scripts in root_counts(ledger):
        lines.append("  %-14s %4d skill(s) %5d script(s)" % (label, skills, scripts))
    return lines


def _top_block(ledger, top):
    if not top:
        return []
    lines = _section("TOP AUTHORITY (%d)" % top)
    ranked = top_skills(ledger, top)
    if not ranked:
        lines.append("  (no skills measured)")
        return lines
    for skill in ranked:
        caps = ",".join(sorted(skill.capabilities)) or "-"
        lines.append(
            "  %-28s %d cap(s) %-40s %d script(s)"
            % (skill.key, len(skill.capabilities), caps, len(skill.scripts))
        )
    return lines


def _unmeasurable_block(ledger):
    if not ledger.unreadable:
        return []
    lines = _section("UNMEASURABLE (%d) -- not a clean result" % len(ledger.unreadable))
    for detail in ledger.unreadable[:MAX_LISTED]:
        lines.append("  " + detail)
    hidden = len(ledger.unreadable) - MAX_LISTED
    if hidden > 0:
        lines.append("  ... and %d more" % hidden)
    return lines


def _excluded_block(ledger):
    if not ledger.excluded:
        return []
    lines = _section("EXCLUDED (%d) -- skipped by rule, listed not hidden" % len(ledger.excluded))
    for detail in ledger.excluded[:MAX_LISTED]:
        lines.append("  " + detail)
    hidden = len(ledger.excluded) - MAX_LISTED
    if hidden > 0:
        lines.append("  ... and %d more" % hidden)
    return lines


def _divergence_block(ledger):
    found = divergence(ledger)
    if not found:
        return []
    lines = _section("DIVERGENT COPIES (%d) -- one name, different content" % len(found))
    for item in found[:MAX_LISTED]:
        lines.append("  %s: %d copies, %d distinct hash(es)" % (item.name, len(item.copies), len(item.hashes)))
        for copy in item.copies:
            lines.append("      %-14s %-40s %s" % (copy.root, copy.rel, copy.sha256[:12]))
    hidden = len(found) - MAX_LISTED
    if hidden > 0:
        lines.append("  ... and %d more" % hidden)
    return lines


def _drift_block(drift):
    if drift is None or not drift:
        return []
    lines = _section("DRIFT vs previous ledger (%d change(s))" % drift.total)
    for key in drift.added[:MAX_LISTED]:
        lines.append("  added    " + key)
    for key in drift.changed[:MAX_LISTED]:
        lines.append("  changed  " + key)
    for key in drift.removed[:MAX_LISTED]:
        lines.append("  removed  " + key)
    return lines


def _frontmatter_block(ledger):
    problems = frontmatter_problems(ledger)
    if not problems:
        return []
    lines = _section("FRONTMATTER PROBLEMS (%d) -- skill still counted" % len(problems))
    for skill in problems[:MAX_LISTED]:
        lines.append("  %-24s %s (%s)" % (skill.key, skill.problem, skill.name))
    return lines


def verdict(ledger, drift=None):
    if ledger.unreadable:
        return EXIT_UNMEASURABLE
    if divergence(ledger):
        return EXIT_FINDING
    if drift:
        return EXIT_FINDING
    return EXIT_CLEAN


def exit_code(ledger, drift=None):
    return verdict(ledger, drift)


VERDICT_TEXT = {
    EXIT_CLEAN: "0 CLEAN - ledger built, no divergent copies, no drift",
    EXIT_FINDING: "1 FINDING - divergent copies or drift since the previous ledger",
    EXIT_UNMEASURABLE: "2 UNMEASURABLE - part of the surface could not be read",
}


def render_text(ledger, drift=None, top=10):
    installed, distinct = skill_counts(ledger)
    lines = [
        "skillbom -- installed skill authority",
        "generated: %s" % (ledger.generated_at or "-"),
        "roots: %d | installed: %s (%d distinct) | %s"
        % (len(ledger.roots), _plural(installed, "skill"), distinct, _plural(script_count(ledger), "script")),
    ]
    for block in (
        _capabilities_block(ledger),
        _roots_block(ledger),
        _drift_block(drift),
        _divergence_block(ledger),
        _top_block(ledger, top),
        _frontmatter_block(ledger),
        _unmeasurable_block(ledger),
        _excluded_block(ledger),
    ):
        lines.extend(block)
    lines.extend(["", "verdict: " + VERDICT_TEXT[verdict(ledger, drift)], ""])
    return "\n".join(lines)
