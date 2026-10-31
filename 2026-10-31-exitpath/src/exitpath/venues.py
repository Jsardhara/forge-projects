"""The venue registry and per-venue exit evaluation.

Registry entries are *declared* selectors, so the mapping from a venue's status page to
"can my funds leave" is reviewable in one place rather than buried in parsing code.
Every URL below was probed live on 2026-10-31 before it was written down; the ones that
did not answer are registered as `uncovered` rather than silently dropped.
"""
import json
from dataclasses import dataclass, field
from typing import Optional, Tuple

from .models import DEGRADED, HALTED, OPEN, UNMEASURABLE, VenueExit, Signal, worst
from .statuspage import Page, Selector, network_from_name, parse_page, select_exit

STATUSPAGE = "statuspage"
UNCOVERED = "uncovered"


@dataclass(frozen=True)
class Venue:
    slug: str
    name: str
    kind: str
    components_url: Optional[str] = None
    selectors: Selector = field(default_factory=Selector)
    network_rule: Optional[str] = None
    probe_url: str = ""
    note: str = ""

    @property
    def status_url(self) -> Optional[str]:
        """statuspage publishes the venue-wide indicator on a separate endpoint."""
        if self.kind != STATUSPAGE or not self.components_url:
            return None
        return self.components_url.replace("/components.json", "/status.json")


VENUES: Tuple[Venue, ...] = (
    Venue(
        slug="kraken",
        name="Kraken",
        kind=STATUSPAGE,
        components_url="https://status.kraken.com/api/v2/components.json",
        selectors=Selector(
            groups=("Digital Currency Funding",),
            patterns=(r"Wire Transfer", r"Cross-Exchange Transfers"),
        ),
        network_rule="kraken_suffix",
        note="850 components; funding group carries per-asset deposit/withdrawal rows",
    ),
    Venue(
        slug="coinbase",
        name="Coinbase",
        kind=STATUSPAGE,
        components_url="https://status.coinbase.com/api/v2/components.json",
        selectors=Selector(groups=("Payment Methods",), patterns=(r"^Stablecoins$",)),
        network_rule="coinbase_plain",
        note="status.coinbase.com runs statuspage.io even though www.coinbase.com/api/v2/status is 404",
    ),
    Venue(
        slug="usdc",
        name="Circle (USDC / EURC issuer)",
        kind=STATUSPAGE,
        components_url="https://status.circle.com/api/v2/components.json",
        selectors=Selector(
            groups=("USDC Bridge", "Circle Cross-Chain Transfer Protocol"),
            patterns=(r"- Redeeming$",),
        ),
        network_rule="circle_usdc",
        note="issuer redeemability is the chain-level exit path; the real page also has EURC rows",
    ),
    Venue(
        slug="binance",
        name="Binance",
        kind=UNCOVERED,
        probe_url="https://status.binance.com/api/v2/status.json",
        note="no statuspage.io (404) and no public JSON status route (404) -- measured 2026-10-31",
    ),
)


def _unique(values):
    """Order-preserving dedupe; drops None. Kraken lists the same network once per asset."""
    out, seen = [], set()
    for value in values:
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return tuple(out)


def _indicator_note_from_page(page: Page) -> Optional[str]:
    if page.indicator and page.indicator not in ("none", "operational"):
        return page.indicator + (" -- " + page.description if page.description else "")
    return None


def _indicator_note(fetch) -> Optional[str]:
    """Venue-wide indicator from api/v2/status.json. Absent or broken -> None, never a guess."""
    if fetch is None or fetch.error or fetch.status != 200:
        return None
    try:
        payload = json.loads(fetch.body.decode("utf-8", "replace"))
    except (ValueError, AttributeError):
        return None
    status = payload.get("status") if isinstance(payload, dict) else None
    if not isinstance(status, dict):
        return None
    indicator = status.get("indicator")
    if not indicator or indicator in ("none", "operational"):
        return None
    description = status.get("description")
    return indicator + (" -- " + description if description else "")


def evaluate_venue(venue: Venue, fetch, indicator_fetch=None) -> VenueExit:
    """Turn one transport result into a VenueExit. Never raises on bad input."""
    if venue.kind == UNCOVERED:
        code = getattr(fetch, "status", 0) or 0
        return VenueExit(
            slug=venue.slug, name=venue.name, kind=venue.kind, state=UNMEASURABLE,
            source_url=venue.probe_url, http_code=code, confidence=0.0,
            reason="no public status JSON (HTTP %s) -- withdrawals not measurable from a public signal" % (code or "?"),
        )

    def unmeasurable(reason, code=0):
        return VenueExit(
            slug=venue.slug, name=venue.name, kind=venue.kind, state=UNMEASURABLE,
            source_url=venue.components_url or "", http_code=code, confidence=0.0, reason=reason,
        )

    if fetch.error:
        return unmeasurable("transport error: %s" % fetch.error, fetch.status)
    if fetch.status != 200:
        return unmeasurable("HTTP %s from %s" % (fetch.status, venue.components_url), fetch.status)

    try:
        payload = json.loads(fetch.body.decode("utf-8", "replace"))
    except (ValueError, AttributeError):
        return unmeasurable("unparseable body (not JSON) from %s" % venue.components_url, fetch.status)

    page: Page = parse_page(payload)
    selected = select_exit(page.components, venue.selectors)
    if not selected:
        return unmeasurable(
            "no exit-relevant component matched (looked for groups=%s patterns=%s)"
            % (list(venue.selectors.groups), list(venue.selectors.patterns)),
            fetch.status,
        )

    signals = []
    group_rows = []
    for group in venue.selectors.groups:
        row = next((c for c in page.components if c.is_group and c.name == group), None)
        if row is not None:
            group_rows.append(row)
            signals.append(Signal(row.name + " (group)", row.state, "parent group state"))
    # Only non-open components are actionable. Kraken publishes 733 per-asset funding rows;
    # echoing them all buries the two that matter, so they are counted (`checked`), not listed.
    for comp in selected:
        if comp.state != OPEN:
            signals.append(Signal(comp.name, comp.state, comp.status))

    # State is computed from every selected component (open ones included) -- deriving it
    # from the reported signals alone would call an all-open venue UNMEASURABLE.
    state = worst([c.state for c in selected] + [r.state for r in group_rows])
    if state not in (OPEN, DEGRADED, HALTED):
        return unmeasurable("components matched but no recognisable status value", fetch.status)

    paused = _unique(network_from_name(s.component, venue.network_rule) for s in signals if s.state == HALTED)
    degraded = _unique(network_from_name(s.component, venue.network_rule) for s in signals if s.state == DEGRADED)
    page_note = _indicator_note(indicator_fetch) or _indicator_note_from_page(page)
    return VenueExit(
        slug=venue.slug, name=venue.name, kind=venue.kind, state=state, signals=tuple(signals),
        paused_networks=paused, degraded_networks=degraded,
        source_url=venue.components_url or "", http_code=fetch.status, confidence=1.0,
        observed_at=page.updated_at, checked=len(selected), page_status=page_note,
    )


def collect_venues(fetcher, venues: Tuple[Venue, ...] = VENUES) -> Tuple[VenueExit, ...]:
    from .models import Fetch

    out = []
    for venue in venues:
        url = venue.components_url or venue.probe_url
        try:
            fetch = fetcher.get(url)
        except Exception as exc:  # noqa: BLE001 - a broken adapter must not kill the run
            fetch = Fetch(0, b"", "%s: %s" % (type(exc).__name__, exc))
        indicator = None
        if venue.status_url:
            try:
                indicator = fetcher.get(venue.status_url)
            except Exception:  # noqa: BLE001 - the indicator is a bonus, not a requirement
                indicator = None
        out.append(evaluate_venue(venue, fetch, indicator))
    return tuple(out)
