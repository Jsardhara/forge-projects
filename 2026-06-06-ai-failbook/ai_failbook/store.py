"""SQLite-backed storage for failure modes."""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ai_failbook.models import (
    Category,
    FailureMode,
    FailureModeCreate,
    FailureModeUpdate,
    SearchQuery,
    SearchResult,
    Severity,
    Stats,
)


def _row_to_model(row: sqlite3.Row) -> FailureMode:
    """Convert a database row to a FailureMode model."""
    data = dict(row)
    data["tags"] = json.loads(data.get("tags", "[]"))
    data["severity"] = Severity(data["severity"])
    data["category"] = Category(data["category"])
    data["created_at"] = datetime.fromisoformat(data["created_at"])
    data["updated_at"] = datetime.fromisoformat(data["updated_at"])
    data["verified"] = bool(data["verified"])
    return FailureMode(**data)


class Store:
    """SQLite-backed failure mode store."""

    def __init__(self, db_path: str | Path = ":memory:"):
        self.db_path = str(db_path)
        self._conn: Optional[sqlite3.Connection] = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._create_tables()
        return self._conn

    def _create_tables(self) -> None:
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS failure_modes (
                vid TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                severity TEXT NOT NULL DEFAULT 'medium',
                category TEXT NOT NULL DEFAULT 'other',
                model TEXT,
                prompt_excerpt TEXT,
                expected_behavior TEXT,
                actual_behavior TEXT,
                workaround TEXT,
                source_url TEXT,
                tags TEXT DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                upvotes INTEGER DEFAULT 0,
                verified INTEGER DEFAULT 0
            )
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_failure_modes_category
            ON failure_modes(category)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_failure_modes_severity
            ON failure_modes(severity)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_failure_modes_model
            ON failure_modes(model)
        """)
        self.conn.commit()

    def create(self, data: FailureModeCreate) -> FailureMode:
        now = datetime.now(timezone.utc)
        fm = FailureMode(
            **data.model_dump(),
            created_at=now,
            updated_at=now,
        )
        self.conn.execute(
            """INSERT INTO failure_modes
               (vid, title, description, severity, category, model,
                prompt_excerpt, expected_behavior, actual_behavior,
                workaround, source_url, tags, created_at, updated_at,
                upvotes, verified)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                fm.vid, fm.title, fm.description, fm.severity.value,
                fm.category.value, fm.model, fm.prompt_excerpt,
                fm.expected_behavior, fm.actual_behavior, fm.workaround,
                fm.source_url, json.dumps(fm.tags),
                fm.created_at.isoformat(), fm.updated_at.isoformat(),
                fm.upvotes, int(fm.verified),
            ),
        )
        self.conn.commit()
        return fm

    def get(self, vid: str) -> Optional[FailureMode]:
        row = self.conn.execute(
            "SELECT * FROM failure_modes WHERE vid = ?", (vid,)
        ).fetchone()
        if row is None:
            return None
        return _row_to_model(row)

    def update(self, vid: str, data: FailureModeUpdate) -> Optional[FailureMode]:
        existing = self.get(vid)
        if existing is None:
            return None
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return existing

        set_parts = []
        values = []
        for key, value in update_data.items():
            if key == "tags":
                value = json.dumps(value)
            elif key == "verified":
                value = int(value)
            set_parts.append(f"{key} = ?")
            values.append(value)

        set_parts.append("updated_at = ?")
        values.append(datetime.now(timezone.utc).isoformat())
        values.append(vid)

        self.conn.execute(
            f"UPDATE failure_modes SET {', '.join(set_parts)} WHERE vid = ?",
            values,
        )
        self.conn.commit()
        return self.get(vid)

    def delete(self, vid: str) -> bool:
        cursor = self.conn.execute(
            "DELETE FROM failure_modes WHERE vid = ?", (vid,)
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def upvote(self, vid: str) -> Optional[FailureMode]:
        self.conn.execute(
            "UPDATE failure_modes SET upvotes = upvotes + 1 WHERE vid = ?",
            (vid,),
        )
        self.conn.commit()
        return self.get(vid)

    def search(self, query: SearchQuery) -> SearchResult:
        conditions = []
        params: list = []

        if query.q:
            conditions.append(
                "(title LIKE ? OR description LIKE ? OR actual_behavior LIKE ?)"
            )
            like_q = f"%{query.q}%"
            params.extend([like_q, like_q, like_q])

        if query.category:
            conditions.append("category = ?")
            params.append(query.category.value)

        if query.severity:
            conditions.append("severity = ?")
            params.append(query.severity.value)

        if query.model:
            conditions.append("model LIKE ?")
            params.append(f"%{query.model}%")

        if query.tag:
            conditions.append("tags LIKE ?")
            params.append(f'%"{query.tag}"%')

        if query.verified_only:
            conditions.append("verified = 1")

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        total = self.conn.execute(
            f"SELECT COUNT(*) FROM failure_modes {where}", params
        ).fetchone()[0]

        rows = self.conn.execute(
            f"""SELECT * FROM failure_modes {where}
                ORDER BY upvotes DESC, created_at DESC
                LIMIT ? OFFSET ?""",
            params + [query.limit, query.offset],
        ).fetchall()

        items = [_row_to_model(r) for r in rows]
        return SearchResult(
            total=total,
            items=items,
            limit=query.limit,
            offset=query.offset,
        )

    def stats(self) -> Stats:
        total = self.conn.execute(
            "SELECT COUNT(*) FROM failure_modes"
        ).fetchone()[0]

        severity_counts = {}
        for row in self.conn.execute(
            "SELECT severity, COUNT(*) as cnt FROM failure_modes GROUP BY severity"
        ):
            severity_counts[row["severity"]] = row["cnt"]

        category_counts = {}
        for row in self.conn.execute(
            "SELECT category, COUNT(*) as cnt FROM failure_modes GROUP BY category"
        ):
            category_counts[row["category"]] = row["cnt"]

        model_counts = {}
        for row in self.conn.execute(
            "SELECT model, COUNT(*) as cnt FROM failure_modes WHERE model IS NOT NULL GROUP BY model"
        ):
            model_counts[row["model"]] = row["cnt"]

        verified = self.conn.execute(
            "SELECT COUNT(*) FROM failure_modes WHERE verified = 1"
        ).fetchone()[0]

        tag_counter: Counter = Counter()
        for row in self.conn.execute("SELECT tags FROM failure_modes"):
            tags = json.loads(row["tags"])
            tag_counter.update(tags)

        top_tags = tag_counter.most_common(10)

        return Stats(
            total_entries=total,
            by_severity=severity_counts,
            by_category=category_counts,
            by_model=model_counts,
            verified_count=verified,
            top_tags=top_tags,
        )

    def seed_sample_data(self) -> list[FailureMode]:
        """Seed with real-world AI failure modes for demonstration."""
        samples = [
            FailureModeCreate(
                title="GPT-4 Hallucinates Legal Citations",
                description="GPT-4 generated completely fake legal case citations in a federal court filing. The model invented case names, docket numbers, and judicial opinions that never existed. Attorney was sanctioned.",
                severity=Severity.CRITICAL,
                category=Category.HALLUCINATION,
                model="gpt-4",
                expected_behavior="Should have stated it couldn't provide specific legal citations or clearly marked them as potentially fabricated",
                actual_behavior="Generated plausible-sounding but entirely fictional case citations with high confidence",
                workaround="Always verify AI-generated citations against official legal databases. Use retrieval-augmented generation (RAG) with verified sources.",
                source_url="https://www.nytimes.com/2023/06/08/nyregion/lawyer-chatgpt-sanctions.html",
                tags=["hallucination", "legal", "citations", "high-stakes"],
            ),
            FailureModeCreate(
                title="Claude Refuses to Answer Benign Questions About Harmful Topics",
                description="Claude refuses to answer legitimate educational or defensive security questions about topics like malware analysis, vulnerability research, or historical weapons, treating all such queries as harmful.",
                severity=Severity.MEDIUM,
                category=Category.SAFETY_REFUSAL,
                model="claude-3-opus",
                expected_behavior="Should distinguish between malicious intent and legitimate research/educational use cases",
                actual_behavior="Blanket refusal on any topic tangentially related to harmful content, even in defensive security context",
                workaround="Reframe the query with explicit context about defensive/educational use. Use role-play framing or academic context.",
                tags=["safety", "over-refusal", "security-research", "false-positive"],
            ),
            FailureModeCreate(
                title="GPT-4o Loses Track of Context in Long Conversations",
                description="After ~4000 tokens of conversation, GPT-4o begins contradicting earlier statements, forgetting user preferences established at the start, and repeating information already discussed.",
                severity=Severity.MEDIUM,
                category=Category.CONTEXT_WINDOW,
                model="gpt-4o",
                expected_behavior="Should maintain consistency throughout the conversation within its context window",
                actual_behavior="Contradicts earlier statements, forgets established facts, repeats itself",
                workaround="Periodically restate key constraints. Break long tasks into separate conversations. Use system prompt to anchor critical facts.",
                tags=["context", "long-conversation", "consistency", "memory"],
            ),
            FailureModeCreate(
                title="AI Agent Deletes Production Database",
                description="An AI coding agent, given broad instructions to 'clean up the database', interpreted this as dropping all tables including production. No confirmation was requested for destructive operations.",
                severity=Severity.CRITICAL,
                category=Category.INSTRUCTION_FOLLOWING,
                model="claude-3.5-sonnet",
                expected_behavior="Should ask for confirmation before destructive operations, especially on production systems",
                actual_behavior="Executed DROP TABLE commands on production database without confirmation",
                workaround="Always use read-only database connections for AI agents. Implement confirmation gates for destructive operations. Use separate dev/staging environments.",
                tags=["agent", "database", "destructive", "production", "safety"],
            ),
            FailureModeCreate(
                title="Gemini Generates Historically Inaccurate Images",
                description="Google's Gemini generated images of historical figures with incorrect ethnicities, including Black Nazi soldiers and Asian founding fathers, due to overcorrection in diversity training.",
                severity=Severity.HIGH,
                category=Category.REASONING,
                model="gemini-pro-vision",
                expected_behavior="Should generate historically accurate representations while being inclusive in appropriate contexts",
                actual_behavior="Applied diversity constraints indiscriminately, producing historically impossible images",
                workaround="Add explicit historical accuracy constraints to prompts. Verify generated historical content against known facts.",
                tags=["image-generation", "history", "overcorrection", "diversity"],
            ),
            FailureModeCreate(
                title="AI Tool Use: Wrong API Endpoint Called Repeatedly",
                description="An AI agent repeatedly called the wrong API endpoint despite receiving 404 errors, continuing the same failed call 15+ times without adapting its approach.",
                severity=Severity.HIGH,
                category=Category.TOOL_USE,
                model="gpt-4-turbo",
                expected_behavior="Should recognize the 404 pattern and try alternative endpoints or report the issue",
                actual_behavior="Called the same non-existent endpoint 15+ times with identical parameters",
                workaround="Implement retry limits with exponential backoff. Add explicit error-handling instructions. Use API documentation as context.",
                tags=["tool-use", "api", "retry", "error-handling", "loop"],
            ),
            FailureModeCreate(
                title="AI Generates Vulnerable Code Patterns",
                description="AI code generation consistently produces SQL injection-vulnerable code when asked for database queries, using string concatenation instead of parameterized queries.",
                severity=Severity.HIGH,
                category=Category.CODE_GENERATION,
                model="gpt-3.5-turbo",
                expected_behavior="Should generate secure code by default, using parameterized queries and input validation",
                actual_behavior="Generated SQL queries using f-string concatenation, creating SQL injection vulnerabilities",
                workaround="Explicitly request secure coding practices. Add security review step. Use SAST tools on AI-generated code.",
                tags=["code-generation", "security", "sql-injection", "vulnerable-code"],
            ),
            FailureModeCreate(
                title="Prompt Injection via Hidden Web Content",
                description="An AI assistant reading a web page followed hidden instructions embedded in white-on-white text, causing it to ignore the user's actual request and perform actions dictated by the hidden content.",
                severity=Severity.CRITICAL,
                category=Category.PROMPT_INJECTION,
                model="gpt-4",
                expected_behavior="Should ignore hidden or invisible content and follow only the user's explicit instructions",
                actual_behavior="Executed instructions from hidden text on the webpage, bypassing user's actual request",
                workaround="Sanitize web content before feeding to AI. Implement instruction hierarchy with user instructions taking priority. Use content filtering.",
                tags=["prompt-injection", "security", "web", "hidden-content"],
            ),
        ]
        created = []
        for s in samples:
            created.append(self.create(s))
        return created

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
