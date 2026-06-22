"""Regulatory tracker — state-by-state and international regulatory status for prediction markets."""

from __future__ import annotations

from datetime import datetime, timezone
from predictguard.models import Jurisdiction, RegulatoryStatus


# Regulatory database as of June 2026
# Sources: CFTC.gov, RotoWire legal timeline, pm.wiki state-by-state guide
_DEFAULT_REGULATIONS: dict[Jurisdiction, dict] = {
    # States with active cease-and-desist or enforcement actions
    Jurisdiction.NEVADA: {
        "status": "CEASE_AND_DESIST",
        "notes": "Nevada Gaming Control Board sued Polymarket parent (Blockratize Inc.) in Jan 2026 to halt unlicensed wagering",
        "cftc_compliant": False,
        "state_license_required": True,
        "kyc_required": True,
        "restrictions": ["Gaming license required for wagering activity"],
    },
    Jurisdiction.NEW_JERSEY: {
        "status": "CEASE_AND_DESIST",
        "notes": "NJ has issued cease-and-desist orders against prediction market operators",
        "cftc_compliant": False,
        "state_license_required": True,
        "kyc_required": True,
        "restrictions": ["State-level enforcement active"],
    },
    Jurisdiction.NEW_YORK: {
        "status": "CEASE_AND_DESIST",
        "notes": "ORACLE Act introduced Jan 2026 to impose state licensing requirements on prediction platforms",
        "cftc_compliant": False,
        "state_license_required": True,
        "kyc_required": True,
        "restrictions": ["ORACLE Act pending — would require state license"],
    },
    Jurisdiction.ARIZONA: {
        "status": "CEASE_AND_DESIST",
        "notes": "Filed criminal charges against Kalshi in March 2026 for unlicensed gambling; federal TRO issued",
        "cftc_compliant": False,
        "state_license_required": True,
        "kyc_required": True,
        "restrictions": ["Criminal charges filed, federal TRO in place"],
    },
    Jurisdiction.MASSACHUSETTS: {
        "status": "RESTRICTED",
        "notes": "Federal judge granted preliminary injunction (Jan 2026) giving state authority to ban Kalshi sports contracts",
        "cftc_compliant": False,
        "state_license_required": True,
        "kyc_required": True,
        "restrictions": ["Sports event contracts restricted by state injunction"],
    },
    # States where prediction markets are generally allowed under CFTC framework
    Jurisdiction.CALIFORNIA: {
        "status": "ALLOWED",
        "notes": "CFTC-regulated platforms available. Fantasy pick'em in gray area.",
        "cftc_compliant": True,
        "state_license_required": False,
        "kyc_required": True,
        "restrictions": [],
    },
    Jurisdiction.TEXAS: {
        "status": "ALLOWED",
        "notes": "CFTC-regulated platforms available",
        "cftc_compliant": True,
        "state_license_required": False,
        "kyc_required": True,
        "restrictions": [],
    },
    Jurisdiction.FLORIDA: {
        "status": "ALLOWED",
        "notes": "CFTC-regulated platforms available",
        "cftc_compliant": True,
        "state_license_required": False,
        "kyc_required": True,
        "restrictions": [],
    },
    Jurisdiction.DELAWARE: {
        "status": "ALLOWED",
        "notes": "CFTC-regulated platforms available",
        "cftc_compliant": True,
        "state_license_required": False,
        "kyc_required": True,
        "restrictions": [],
    },
    # International
    Jurisdiction.UNITED_KINGDOM: {
        "status": "RESTRICTED",
        "notes": "FCA has not authorized prediction market platforms for retail access. May be classified as gambling.",
        "cftc_compliant": False,
        "state_license_required": True,
        "kyc_required": True,
        "restrictions": ["Gambling Commission oversight likely required"],
    },
    Jurisdiction.EUROPEAN_UNION: {
        "status": "UNCLEAR",
        "notes": "Classification uncertainty: MiFID II if financial instruments, national gambling regs if betting. MiCA covers crypto-assets but not event contracts.",
        "cftc_compliant": False,
        "state_license_required": False,
        "kyc_required": True,
        "restrictions": ["Regulatory classification pending"],
    },
    Jurisdiction.CANADA: {
        "status": "UNCLEAR",
        "notes": "Provincial gambling regulators have not issued clear guidance on prediction markets",
        "cftc_compliant": False,
        "state_license_required": False,
        "kyc_required": True,
        "restrictions": [],
    },
    Jurisdiction.AUSTRALIA: {
        "status": "RESTRICTED",
        "notes": "ACMA has not authorized prediction market platforms. Likely classified as gambling.",
        "cftc_compliant": False,
        "state_license_required": True,
        "kyc_required": True,
        "restrictions": ["Gambling license likely required"],
    },
    Jurisdiction.JAPAN: {
        "status": "RESTRICTED",
        "notes": "Financial Services Agency has not authorized prediction markets. Gambling laws apply.",
        "cftc_compliant": False,
        "state_license_required": True,
        "kyc_required": True,
        "restrictions": ["Gambling laws apply"],
    },
    Jurisdiction.SINGAPORE: {
        "status": "RESTRICTED",
        "notes": "MAS has not authorized prediction markets. Gambling laws apply.",
        "cftc_compliant": False,
        "state_license_required": True,
        "kyc_required": True,
        "restrictions": ["Gambling laws apply"],
    },
}


class RegulatoryTracker:
    """Tracks regulatory status across jurisdictions."""

    def __init__(self) -> None:
        self._regulations: dict[Jurisdiction, RegulatoryStatus] = {}
        self._load_defaults()

    def _load_defaults(self) -> None:
        for juris, data in _DEFAULT_REGULATIONS.items():
            self._regulations[juris] = RegulatoryStatus(
                jurisdiction=juris,
                status=data["status"],
                notes=data["notes"],
                cftc_compliant=data["cftc_compliant"],
                state_license_required=data["state_license_required"],
                kyc_required=data["kyc_required"],
                restrictions=list(data["restrictions"]),
                last_updated=datetime.now(timezone.utc),
            )

    def get_status(self, jurisdiction: Jurisdiction) -> RegulatoryStatus | None:
        """Get regulatory status for a jurisdiction."""
        return self._regulations.get(jurisdiction)

    def update_status(self, status: RegulatoryStatus) -> None:
        """Update regulatory status for a jurisdiction."""
        self._regulations[status.jurisdiction] = status

    def get_all(self) -> list[RegulatoryStatus]:
        """Get all regulatory statuses."""
        return list(self._regulations.values())

    def get_by_status(self, status: str) -> list[RegulatoryStatus]:
        """Get all jurisdictions with a given status."""
        return [r for r in self._regulations.values() if r.status == status]

    def get_restricted(self) -> list[RegulatoryStatus]:
        """Get all restricted/blocked jurisdictions."""
        blocked = {"CEASE_AND_DESIST", "BAN_PROPOSED", "RESTRICTED"}
        return [r for r in self._regulations.values() if r.status in blocked]

    def is_trade_allowed(self, jurisdiction: Jurisdiction, platform_cftc_compliant: bool = False) -> tuple[bool, str]:
        """Check if a trade is allowed in a given jurisdiction.

        Returns (allowed: bool, reason: str).
        """
        reg = self._regulations.get(jurisdiction)
        if reg is None:
            return False, f"Unknown jurisdiction: {jurisdiction.value} — default deny"

        if reg.status == "ALLOWED":
            return True, "Allowed under CFTC framework"

        if reg.status == "CEASE_AND_DESIST":
            return False, f"CEASE_AND_DESIST order active: {reg.notes}"

        if reg.status == "BAN_PROPOSED":
            return False, f"Ban proposed: {reg.notes}"

        if reg.status == "RESTRICTED":
            if platform_cftc_compliant and reg.cftc_compliant:
                return True, "Allowed — CFTC-compliant platform"
            return False, f"Restricted: {reg.notes}"

        if reg.status == "UNCLEAR":
            return False, f"Regulatory status unclear — default deny: {reg.notes}"

        return False, f"Unknown status: {reg.status}"

    def compliance_check(self, trades: list) -> list[str]:
        """Run compliance checks against a list of trades.

        Returns list of findings (empty = fully compliant).
        """
        findings: list[str] = []
        for trade in trades:
            if trade.jurisdiction is not None:
                allowed, reason = self.is_trade_allowed(
                    trade.jurisdiction,
                    platform_cftc_compliant=(trade.platform in ("kalshi", "polymarket_us", "crypto_com")),
                )
                if not allowed:
                    findings.append(
                        f"Trade {trade.tid}: NOT ALLOWED in {trade.jurisdiction.value} — {reason}"
                    )
        return findings

    def summary(self) -> dict[str, int]:
        """Return a count of jurisdictions by status."""
        counts: dict[str, int] = {}
        for reg in self._regulations.values():
            counts[reg.status] = counts.get(reg.status, 0) + 1
        return counts
