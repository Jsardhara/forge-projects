"""Breach sources.

A ``BreachSource`` is anything that can be queried for whether an identity
value has appeared in a breach. Two implementations ship:

- ``LocalSource``: loads breach records from a local JSONL/JSON file. Network
  free, used for tests and for ingesting your own dumps/paste files.
- ``HIBPSource``: talks to the HaveIBeenPwned v3 API (email/password) and the
  Pwned Passwords range API. Network access + an API key are required; the
  email lookup uses TLS. If no API key is configured it degrades gracefully
  (returns no records) so the rest of the tool still works offline.
"""

from __future__ import annotations

import hashlib
import json
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

from breach_sentinel.models import (
    BreachRecord,
    BreachSourceInfo,
    BreachType,
)


class BreachSource(ABC):
    @abstractmethod
    def info(self) -> BreachSourceInfo: ...

    @abstractmethod
    def query(self, value: str, breach_type: Optional[BreachType] = None) -> list[BreachRecord]:
        """Return breach records for the given identity value."""
        ...


class LocalSource(BreachSource):
    """Loads breach records from a local file (JSON list or JSONL).

    Expected record shape (per line or per element)::

        {
          "identity_value": "alice@example.com",
          "breach_type": "email",
          "breach_name": "Adobe 2013",
          "breach_date": "2013-10-04",     # optional
          "description": "..."             # optional
        }

    ``identity_value`` can also be a list to register the same breach under
    multiple values.
    """

    def __init__(self, sid: str, path: str, name: Optional[str] = None):
        self._sid = sid
        self._path = path
        self._name = name or sid

    def info(self) -> BreachSourceInfo:
        return BreachSourceInfo(
            sid=self._sid,
            name=self._name,
            source_type="local",
            description=f"Local breach dump loaded from {self._path}",
        )

    def _load(self) -> list[dict]:
        records: list[dict] = []
        with open(self._path, "r", encoding="utf-8") as fh:
            text = fh.read().strip()
        if not text:
            return records
        if text.lstrip().startswith("["):
            data = json.loads(text)
            if isinstance(data, list):
                records = data
        else:
            for line in text.splitlines():
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def query(self, value: str, breach_type: Optional[BreachType] = None) -> list[BreachRecord]:
        out: list[BreachRecord] = []
        seen = set()
        target = value.strip().lower()
        for rec in self._load():
            vals = rec.get("identity_value")
            if isinstance(vals, str):
                vals = [vals]
            if not isinstance(vals, list):
                continue
            if target not in [v.strip().lower() for v in vals]:
                continue
            btype = BreachType(rec.get("breach_type", "other"))
            if breach_type is not None and btype != breach_type:
                continue
            bname = rec.get("breach_name", "unknown")
            bdate_raw = rec.get("breach_date")
            bdate = _parse_date(bdate_raw) if bdate_raw else None
            bid = BreachRecord.make_bid(self._sid, target, btype, bname)
            if bid in seen:
                continue
            seen.add(bid)
            out.append(
                BreachRecord(
                    bid=bid,
                    source_id=self._sid,
                    identity_value=target,
                    breach_type=btype,
                    breach_name=bname,
                    breach_date=bdate,
                    description=rec.get("description", ""),
                )
            )
        return out


class HIBPSource(BreachSource):
    """HaveIBeenPwned integration (email breach lookup + Pwned Passwords).

    Requires an API key (https://haveibeenpwned.com/API/Key). Without a key
    ``query`` returns no records (safe offline degradation).
    """

    BASE = "https://haveibeenpwned.com/api/v3"

    def __init__(self, api_key: Optional[str] = None, user_agent: str = "BreachSentinel/0.1"):
        self._api_key = api_key
        self._ua = user_agent

    def info(self) -> BreachSourceInfo:
        return BreachSourceInfo(
            sid="hibp",
            name="HaveIBeenPwned",
            source_type="api",
            description="HIBP v3 breaches API + Pwned Passwords range API",
        )

    def _headers(self) -> dict:
        h = {"User-Agent": self._ua}
        if self._api_key:
            h["hibp-api-key"] = self._api_key
        return h

    def query(self, value: str, breach_type: Optional[BreachType] = None) -> list[BreachRecord]:
        if not self._api_key:
            return []
        out: list[BreachRecord] = []
        val = value.strip()
        # Email / account breach lookup
        email_like = "@" in val and "." in val.split("@")[-1]
        if (breach_type is None or breach_type == BreachType.EMAIL) and email_like:
            out.extend(self._query_account(val))
        # Pwned Passwords (range / k-anonymity)
        if breach_type is None or breach_type == BreachType.PASSWORD:
            out.extend(self._query_password(val))
        return out

    def _query_account(self, email: str) -> list[BreachRecord]:
        try:
            import urllib.request

            url = f"{self.BASE}/breachedaccount/{urllib.parse.quote(email)}?truncateResponse=false"
            req = urllib.request.Request(url, headers=self._headers())
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception:
            return []
        out: list[BreachRecord] = []
        for breach in data:
            name = breach.get("Name", "unknown")
            bdate = _parse_date(breach.get("BreachDate"))
            bid = BreachRecord.make_bid("hibp", email.lower(), BreachType.EMAIL, name)
            out.append(
                BreachRecord(
                    bid=bid,
                    source_id="hibp",
                    identity_value=email.lower(),
                    breach_type=BreachType.EMAIL,
                    breach_name=name,
                    breach_date=bdate,
                    description=breach.get("Description", ""),
                )
            )
        return out

    def _query_password(self, pw: str) -> list[BreachRecord]:
        try:
            import urllib.request

            sha = hashlib.sha1(pw.encode("utf-8")).hexdigest().upper()
            prefix, suffix = sha[:5], sha[5:]
            url = f"https://api.pwnedpasswords.com/range/{prefix}"
            req = urllib.request.Request(url, headers=self._headers())
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = resp.read().decode("utf-8")
        except Exception:
            return []
        for line in body.splitlines():
            parts = line.split(":")
            if parts and parts[0].strip().upper() == suffix:
                try:
                    count = int(parts[1].strip())
                except ValueError:
                    count = 0
                bid = BreachRecord.make_bid("hibp", pw, BreachType.PASSWORD, "PwnedPasswords")
                return [
                    BreachRecord(
                        bid=bid,
                        source_id="hibp",
                        identity_value="<redacted>",
                        breach_type=BreachType.PASSWORD,
                        breach_name="PwnedPasswords",
                        password_pwned_count=count,
                        description=f"Password found in {count} known breaches",
                    )
                ]
        return []


def _parse_date(raw: str) -> Optional[datetime]:
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%Y/%m/%d"):
        try:
            dt = datetime.strptime(raw, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None
