"""US state data-breach notification compliance triage for idguard.

This is REFERENCE triage material for security responders, NOT legal advice.
Notification windows are drawn from publicly available summaries of state
data-breach notification statutes; exact values vary with statute amendments,
entity type (financial institution covered by GLBA/FCRA, HIPAA-covered
entities), and the attorney general guidance in effect. ALWAYS verify the
current statute before notifying. `None` window = "in the most expedient time
possible and without unreasonable delay" (statute specifies no fixed number of
days) or otherwise not a fixed days value.
"""

from __future__ import annotations

from typing import Dict, List, Optional

# state code -> {days: fixed window or None, note}
_STATE: Dict[str, Dict[str, object]] = {
    "AL": {"days": None, "note": "alert AG if affecting 1000+ residents"},
    "AK": {"days": 30, "note": "most expedient; 30-day presumption often cited"},
    "AZ": {"days": None, "note": "in the most expedient time and without unreasonable delay"},
    "AR": {"days": None, "note": "most expedient time and without unreasonable delay"},
    "CA": {"days": None, "note": "most expedient; notify affected + AG; medical/email: 24h"},
    "CO": {"days": 30, "note": "AG notification when 500+ Colorado residents"},
    "CT": {"days": None, "note": "most expedient and no unreasonable delay"},
    "DE": {"days": None, "note": "notify AG; no unreasonable delay"},
    "DC": {"days": None, "note": "most expedient and without unreasonable delay"},
    "FL": {"days": 30, "note": "within 30 days of breach determination; also AG"},
    "GA": {"days": None, "note": "no unreasonable delay"},
    "HI": {"days": None, "note": "most expedient and without unreasonable delay"},
    "ID": {"days": None, "note": "no unreasonable delay; AG when 1000+"},
    "IL": {"days": None, "note": "most expedient. PIPA; AG when 500+"},
    "IN": {"days": None, "note": "most expedient and without unreasonable delay"},
    "IA": {"days": None, "note": "no unreasonable delay"},
    "KS": {"days": None, "note": "without unreasonable delay"},
    "KY": {"days": None, "note": "most expedient and no unreasonable delay"},
    "LA": {"days": None, "note": "no unreasonable delay"},
    "ME": {"days": None, "note": "most expedient and without unreasonable delay"},
    "MD": {"days": 45, "note": "AG notification within 45 days"},
    "MA": {"days": None, "note": "as soon as practicable; AG + Dir. Consumer Affairs"},
    "MI": {"days": None, "note": "no unreasonable delay"},
    "MN": {"days": None, "note": "most expedient and without unreasonable delay"},
    "MS": {"days": None, "note": "AG within 45 days is common practice"},
    "MO": {"days": None, "note": "without unreasonable delay"},
    "MT": {"days": None, "note": "no unreasonable delay; AG if 1000+"},
    "NE": {"days": None, "note": "most expedient and without unreasonable delay"},
    "NV": {"days": None, "note": "no unreasonable delay"},
    "NH": {"days": None, "note": "most expedient and without unreasonable delay"},
    "NJ": {"days": None, "note": "most expedient and without unreasonable delay"},
    "NM": {"days": None, "note": "no unreasonable delay"},
    "NY": {"days": None, "note": "as expedient as possible; AG if 500+"},
    "NC": {"days": None, "note": "no unreasonable delay; AG if 1000+"},
    "ND": {"days": None, "note": "most expedient and without unreasonable delay"},
    "OH": {"days": None, "note": "no unreasonable delay; AG if 500+"},
    "OK": {"days": None, "note": "most expedient and without unreasonable delay"},
    "OR": {"days": 45, "note": "AG if 500+; within 45 days"},
    "PA": {"days": None, "note": "most expedient and without unreasonable delay"},
    "RI": {"days": 45, "note": "no more than 45 days from confirmed breach"},
    "SC": {"days": None, "note": "most expedient and without unreasonable delay"},
    "SD": {"days": None, "note": "no specific deadline; state AG"},
    "TN": {"days": None, "note": "no unreasonable delay"},
    "TX": {"days": None, "note": "without unreasonable delay; AG if 25K+ (min. data elements)"},
    "UT": {"days": None, "note": "most expedient and without unreasonable delay"},
    "VT": {"days": 45, "note": "no longer than 45 days after knowing of the breach"},
    "VA": {"days": 45, "note": "AG notification within 45 days of confirmation"},
    "WA": {"days": 45, "note": "AG if 500+; no later than 45 days"},
    "WV": {"days": None, "note": "no unreasonable delay; AG if 1000+"},
    "WI": {"days": None, "note": "most expedient and without unreasonable delay"},
    "WY": {"days": None, "note": "without unreasonable delay"},
    "PR": {"days": None, "note": "most expedient; notifies Dept. of Consumer Affairs"},
    "VI": {"days": None, "note": "according to regulation"},
}

_REQUIRED_CONTENT = [
    "a description of the breach (what happened, in plain language)",
    "the date (or estimated date) of the breach",
    "the type of personal information involved",
    "what the company has done to protect affected individuals",
    "what affected individuals can do to protect themselves",
    "a way to contact the company (toll-free number / website) for more info",
]

_REMEDIATION = [
    "place a free fraud alert or credit freeze at each of the three credit bureaus "
    "(Equifax, Experian, TransUnion — freeze is free under federal law)",
    "file an identity-theft report / recovery plan at identitytheft.gov (FTC)",
    "request a free copy of your credit report (annualcreditreport.com)",
    "request an IRS Identity Protection PIN (for tax-related identity theft)",
    "monitor account statements and set up transaction alerts for 12+ months",
    "change and strengthen passwords; enable 2FA on sensitive accounts",
]

REAL_STATES = sorted({k for k in _STATE if k not in ("DC2",)})


def lookup_state(code: str) -> Dict[str, object]:
    """Return the matrix entry for a state code (upper). Raises KeyError if unknown."""
    return _STATE[code.upper()]


def build_notification_plan(
    state_codes: Optional[List[str]] = None,
    affected_subscribers: int = 0,
    affected_residents: int = 0,
    evidence_summary: str = "",
) -> str:
    """Render a breach-notification triage plan for the given states (default all
    REAL_STATES). Returns markdown. Includes explicit 'not legal advice' caveat."""
    states = sorted({s for s in (state_codes or REAL_STATES) if s in _STATE and s != "DC2"})
    lines: List[str] = []
    lines.append("# idguard — Data-Breach Notification Triage (REFERENCE)")
    lines.append("")
    lines.append("> NOT legal advice. Verify the current statute and your entity type "
                 "(state law vs GLBA/FCRA/HIPAA) before notifying. Fixed windows vary "
                 "with amendments; `no fixed window` = statute says most expedient time "
                 "without unreasonable delay.")
    if evidence_summary:
        lines.append("")
        lines.append(f"Scope: {evidence_summary}")
    lines.append("")
    lines.append(f"Affected subscribers: {affected_subscribers} | Affected residents "
                 f"in covered states: {affected_residents}")
    lines.append("")
    lines.append("| State | Report to AG/Regulator | Notification window | Note |")
    lines.append("|-------|----------------------|--------------------|------|")
    for code in states:
        e = _STATE[code]
        days = e["days"]
        win = f"{days} days" if isinstance(days, int) else "no fixed window"
        note = str(e["note"])
        lines.append(f"| {code} | required | {win} | {note} |")
    lines.append("")
    lines.append("## Notification letter — required content (common across states)")
    for i, item in enumerate(_REQUIRED_CONTENT, 1):
        lines.append(f"{i}. {item}")
    lines.append("")
    lines.append("## Remediation steps for affected individuals")
    for i, item in enumerate(_REMEDIATION, 1):
        lines.append(f"{i}. {item}")
    lines.append("")
    lines.append("Sources to verify: your attorney general's breach-notification "
                 "statute, the FTC Data Breach Response Guide, and the NCSL state "
                 "summary table.")
    return "\n".join(lines)