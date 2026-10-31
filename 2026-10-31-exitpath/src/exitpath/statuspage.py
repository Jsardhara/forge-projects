"""Parse statuspage.io component payloads into exit-relevant components.

Kept pure: no network, no clock, no filesystem. Everything here is a function of the
payload, which is what makes the real recorded payloads in tests/fixtures a valid test.
"""
import json
import re
from dataclasses import dataclass
from typing import Optional, Tuple

from .models import COMPONENT_STATE


@dataclass(frozen=True)
class Component:
    name: str
    status: str
    parent: Optional[str] = None
    is_group: bool = False

    @property
    def state(self):
        return COMPONENT_STATE.get(self.status, "unknown")


@dataclass(frozen=True)
class Selector:
    """How to find the components that say whether value can leave this venue."""

    groups: Tuple[str, ...] = ()
    patterns: Tuple[str, ...] = ()


@dataclass(frozen=True)
class Page:
    components: Tuple[Component, ...]
    updated_at: Optional[str] = None
    name: str = ""
    indicator: Optional[str] = None
    description: Optional[str] = None


def _index(payload):
    comps = payload.get("components") or []
    names = {}
    for c in comps:
        if isinstance(c, dict) and c.get("id") is not None:
            names[c["id"]] = c.get("name")
    return comps, names


def parse_page(payload) -> Page:
    """Build a Page, resolving each child's parent name through its group_id."""
    if not isinstance(payload, dict):
        return Page(())
    comps, names = _index(payload)
    out = []
    for c in comps:
        if not isinstance(c, dict):
            continue
        gid = c.get("group_id")
        out.append(
            Component(
                name=str(c.get("name") or ""),
                status=str(c.get("status") or "unknown"),
                parent=names.get(gid) if gid else None,
                is_group=c.get("group") is True,
            )
        )
    page = payload.get("page")
    page = page if isinstance(page, dict) else {}
    status = payload.get("status")
    status = status if isinstance(status, dict) else {}
    return Page(
        tuple(out),
        page.get("updated_at"),
        str(page.get("name") or ""),
        status.get("indicator"),
        status.get("description"),
    )


def parse_components(payload) -> Tuple[Component, ...]:
    return parse_page(payload).components


def select_exit(components, selector: Selector) -> Tuple[Component, ...]:
    """Child components that bear on exit: by parent group name or by name pattern.

    Group rows themselves are excluded -- they are the heading, not a measurement. The
    venue layer adds the heading's own state back in, so a degraded parent is not lost.
    """
    compiled = [re.compile(p, re.IGNORECASE) for p in selector.patterns]
    seen = set()
    picked = []
    for c in components:
        if c.is_group or not c.name:
            continue
        by_group = c.parent is not None and c.parent in selector.groups
        by_pattern = any(rx.search(c.name) for rx in compiled)
        if (by_group or by_pattern) and c.name not in seen:
            seen.add(c.name)
            picked.append(c)
    return tuple(picked)


def network_from_name(name: str, rule: Optional[str]) -> Optional[str]:
    """Extract the network/rail a component name refers to, per venue naming style."""
    if not rule:
        return None
    parts = [p.strip() for p in name.split(" - ")]
    if rule == "kraken_suffix" and len(parts) >= 2:
        return parts[-1] or None
    if rule == "circle_usdc" and len(parts) >= 3:
        return parts[1] or None
    if rule == "coinbase_plain":
        return None
    return None
