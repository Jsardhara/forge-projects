"""Cost & Usage Report (CUR) CSV parser for costrecon.

Supports both the full AWS CUR column naming (``lineItem/UnblendedCost``,
``product/ProductName``, ...) and a simplified single-level schema. Robust to
missing columns and to credits / negative line items.
"""

import csv
from typing import Dict, List, Optional

from .models import LineItem

# Map a normalized field name -> candidate CUR column headers (in priority order).
_COLUMN_ALIASES = {
    "line_item_id": ["lineItem/LineItemId", "identity/LineItemId", "LineItemId", "id"],
    "account_id": ["lineItem/UsageAccountId", "UsageAccountId", "account_id", "AccountId"],
    "service": ["product/ProductName", "lineItem/ProductCode", "ProductName", "Service", "service"],
    "region": ["lineItem/Region", "Region", "region"],
    "usage_type": ["lineItem/UsageType", "UsageType", "usage_type"],
    "description": ["lineItem/LineItemDescription", "LineItemDescription", "description", "Description"],
    "cost": ["lineItem/UnblendedCost", "lineItem/BlendedCost", "UnblendedCost", "cost", "Cost"],
    "usage_quantity": ["lineItem/UsageQuantity", "UsageQuantity", "usage_quantity", "quantity"],
    "resource_id": ["lineItem/ResourceId", "ResourceId", "resource_id", "Resource"],
    "period_start": ["lineItem/UsageStartDate", "UsageStartDate", "period_start"],
    "period_end": ["lineItem/UsageEndDate", "UsageEndDate", "period_end"],
}


def _resolve_columns(fieldnames) -> Dict[str, str]:
    """Return {normalized_field: actual_header} for the given CSV header row."""
    present = set(fieldnames or [])
    resolved = {}
    for norm, candidates in _COLUMN_ALIASES.items():
        for cand in candidates:
            if cand in present:
                resolved[norm] = cand
                break
    return resolved


def _to_float(value: Optional[str], default: float = 0.0) -> float:
    if value is None:
        return default
    s = str(value).strip().replace(",", "")
    if s == "" or s.lower() in ("nan", "n/a", "na"):
        return default
    try:
        return float(s)
    except ValueError:
        return default


def parse_cur(path: str) -> List[LineItem]:
    """Parse a CUR CSV file into normalized LineItem objects."""
    items: List[LineItem] = []
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        cols = _resolve_columns(reader.fieldnames)
        if "cost" not in cols:
            raise ValueError(
                "CUR missing a recognizable cost column "
                "(expected one of: lineItem/UnblendedCost, cost, ...)"
            )
        for i, row in enumerate(reader):
            if row is None:
                continue
            get = lambda n: row.get(cols.get(n, ""), "")
            service = (get("service") or "UNKNOWN").strip() or "UNKNOWN"
            li = LineItem(
                line_item_id=str(get("line_item_id") or f"row-{i}"),
                account_id=str(get("account_id") or "UNKNOWN"),
                service=service,
                region=str(get("region") or ""),
                usage_type=str(get("usage_type") or ""),
                description=str(get("description") or ""),
                cost=_to_float(get("cost")),
                usage_quantity=_to_float(get("usage_quantity")),
                resource_id=str(get("resource_id") or ""),
                period_start=(get("period_start") or None),
                period_end=(get("period_end") or None),
            )
            items.append(li)
    return items


def summarize_by_service(items: List[LineItem], split_region: bool = False) -> Dict[str, float]:
    """Sum unblended cost per service (or per ``service|region`` if split_region)."""
    totals: Dict[str, float] = {}
    for it in items:
        key = f"{it.service}|{it.region}" if split_region else it.service
        totals[key] = totals.get(key, 0.0) + it.cost
    return totals
