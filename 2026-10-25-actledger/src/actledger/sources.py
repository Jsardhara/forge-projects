"""Adapters that turn an existing runtime's own records into ledger records.

These exist so the ledger can be seeded from what a fleet has already done, not only from
actions recorded after installation. The mapping is deliberately literal and lossy in the
honest direction: if the source system never recorded a policy version or a named
verifier, the field stays empty and the audit reports it. Filling those in from a guess
would manufacture the exact false assurance this tool is built to find.
"""

import hashlib
import sqlite3
from datetime import datetime, timezone
from typing import List, Optional

from .models import ActionRecord


class SourceError(Exception):
    """Raised when a runtime database cannot be read or does not have the expected shape."""


def _iso(epoch: Optional[int]) -> str:
    if not epoch:
        return ""
    return datetime.fromtimestamp(int(epoch), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest() if text else ""


def records_from_kanban(
    path: str, limit: Optional[int] = None, profile: Optional[str] = None
) -> List[ActionRecord]:
    """One record per `task_runs` row — a run is a real unit of agent work.

    Hermes' kanban records who ran the task, when, and how it ended. It does not record a
    named verifier, a policy version or a model weights digest, so those fields are left
    empty here and surface as audit findings rather than being invented.
    """
    try:
        connection = sqlite3.connect("file:%s?mode=ro" % path, uri=True)
    except sqlite3.Error as exc:
        raise SourceError("cannot open kanban database %s: %s" % (path, exc))

    query = """
        SELECT r.id, r.task_id, r.profile, r.status, r.outcome, r.started_at, r.ended_at,
               COALESCE(t.assignee, ''), COALESCE(t.title, ''), COALESCE(t.body, ''),
               COALESCE(t.model_override, '')
        FROM task_runs AS r
        LEFT JOIN tasks AS t ON t.id = r.task_id
    """
    params = []
    if profile:
        query += " WHERE r.profile = ?"
        params.append(profile)
    query += " ORDER BY r.started_at ASC, r.id ASC"
    if limit:
        query += " LIMIT ?"
        params.append(int(limit))

    try:
        rows = connection.execute(query, params).fetchall()
    except sqlite3.Error as exc:
        raise SourceError("kanban database %s is not readable as expected: %s" % (path, exc))
    finally:
        connection.close()

    records = []
    for (
        run_id,
        task_id,
        run_profile,
        status,
        outcome,
        started_at,
        ended_at,
        assignee,
        title,
        body,
        model_override,
    ) in rows:
        records.append(
            ActionRecord(
                agent_id=(assignee or run_profile or "unknown").strip(),
                tool="kanban.run",
                outcome=(outcome or status or "unknown").strip(),
                ts=_iso(started_at),
                model_id=(model_override or "").strip(),
                model_digest="",
                policy_version="",
                args_hash=_digest(body or title),
                data_touched=(task_id,),
                verifier="",
                approved_by="",
                approved_at="",
            )
        )
    return records
