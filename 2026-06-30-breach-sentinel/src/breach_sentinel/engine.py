"""Scan engine — ties sources, scorer, alerting, and store together."""

from __future__ import annotations

from typing import Iterable, Optional

from breach_sentinel.alerting import build_alerts
from breach_sentinel.models import (
    BreachRecord,
    BreachSourceInfo,
    Identity,
    ScanResult,
)
from breach_sentinel.scorer import score_exposure
from breach_sentinel.store import SentinelStore
from breach_sentinel.sources import BreachSource


class SentinelEngine:
    """Coordinates scan + persistence for a set of breach sources."""

    def __init__(self, sources: Iterable[BreachSource], store: Optional[SentinelStore] = None):
        self.sources: list[BreachSource] = list(sources)
        self.store = store

    def source_info(self) -> list[BreachSourceInfo]:
        return [s.info() for s in self.sources]

    def scan_identity(self, identity: Identity) -> ScanResult:
        records: list[BreachRecord] = []
        for source in self.sources:
            for value in identity.search_keys():
                # Query without a type filter: a value (e.g. an email) may
                # appear in multiple breach types, and sources like HIBP need
                # the raw value to run their own lookups.
                records.extend(source.query(value))
        score = score_exposure(identity.iid, records)
        alerts = build_alerts(identity, records)

        if self.store is not None:
            self.store.add_identity(identity)
            self.store.add_breaches(records)
            self.store.add_alerts(alerts)
            result = ScanResult(
                iid=identity.iid, label=identity.label,
                records=tuple(records), score=score, alerts=tuple(alerts),
            )
            self.store.record_scan(result)
            return result

        return ScanResult(
            iid=identity.iid, label=identity.label,
            records=tuple(records), score=score, alerts=tuple(alerts),
        )
