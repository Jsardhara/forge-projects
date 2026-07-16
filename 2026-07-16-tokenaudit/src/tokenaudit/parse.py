"""Transcript parsers for tokenaudit.

Supports two formats:
  * Claude Code session JSONL (``~/.claude/projects/.../*.jsonl``) -- each line is a
    ``{"type":"user"|"assistant"|..., "message": {...}}`` blob with ``message.usage``
    carrying ``input_tokens``/``output_tokens`` and content blocks describing tool calls.
  * Generic JSONL -- one JSON object per line: ``{"role":.., "usage":{...}, "model":..}``
    where usage may use ``input_tokens``/``output_tokens`` OR ``prompt_tokens``/
    ``completion_tokens``.

The parser is deliberately tolerant: malformed/blank lines are skipped, and content
that is a plain string (not a block list) is handled.
"""
from __future__ import annotations

import json
from typing import Iterable, List

from .models import Message, Session, Usage

_READ_TOOL_NAMES = {"read", "readfile", "read_file", "cat"}


def _as_usage(obj: dict) -> Usage:
    if not isinstance(obj, dict):
        return Usage()
    # Claude-style
    inp = obj.get("input_tokens", 0) or 0
    out = obj.get("output_tokens", 0) or 0
    # Generic-style aliases
    if not inp and not out:
        inp = obj.get("prompt_tokens", 0) or 0
        out = obj.get("completion_tokens", 0) or 0
    cc = obj.get("cache_creation_input_tokens", 0) or 0
    cr = obj.get("cache_read_input_tokens", 0) or 0
    return Usage(
        input_tokens=int(inp),
        output_tokens=int(out),
        cache_creation_tokens=int(cc),
        cache_read_tokens=int(cr),
    )


def _content_blocks(content) -> List[dict]:
    if isinstance(content, list):
        return [b for b in content if isinstance(b, dict)]
    return []


def _scan_assistant(content) -> tuple[bool, tuple]:
    blocks = _content_blocks(content)
    has_tool_use = any(b.get("type") == "tool_use" for b in blocks)
    reads: List[str] = []
    if has_tool_use:
        for b in blocks:
            if b.get("type") == "tool_use":
                name = (b.get("name") or "").lower()
                if name in _READ_TOOL_NAMES:
                    inp = b.get("input") or {}
                    fp = inp.get("file_path") or inp.get("path")
                    if fp:
                        reads.append(str(fp))
    return has_tool_use, tuple(reads)


def _scan_user(content) -> bool:
    blocks = _content_blocks(content)
    return any(b.get("type") == "tool_result" for b in blocks)


def messages_from_claude_jsonl(text: str) -> List[Message]:
    msgs: List[Message] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        msg = obj.get("message")
        if not isinstance(msg, dict):
            continue
        role = msg.get("role", obj.get("type", "unknown"))
        content = msg.get("content")
        has_tool_use, reads = _scan_assistant(content)
        has_tool_result = _scan_user(content)
        # usage may live on the message or on the outer object
        usage_obj = msg.get("usage") or obj.get("usage") or {}
        msgs.append(
            Message(
                role=str(role),
                usage=_as_usage(usage_obj),
                model=msg.get("model"),
                content=content,
                has_tool_use=has_tool_use,
                has_tool_result=has_tool_result,
                file_reads=reads,
            )
        )
    return msgs


def messages_from_generic_jsonl(text: str) -> List[Message]:
    msgs: List[Message] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        role = obj.get("role", "unknown")
        content = obj.get("content")
        has_tool_use, reads = _scan_assistant(content)
        has_tool_result = _scan_user(content)
        msgs.append(
            Message(
                role=str(role),
                usage=_as_usage(obj.get("usage") or {}),
                model=obj.get("model"),
                content=content,
                has_tool_use=has_tool_use,
                has_tool_result=has_tool_result,
                file_reads=reads,
            )
        )
    return msgs


def _looks_claude(lines: Iterable[str]) -> bool:
    for line in lines:
        s = line.strip()
        if not s:
            continue
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and "message" in obj:
            return True
        return False
    return False


def parse_session(path: str) -> Session:
    """Read a transcript file and parse it into a Session, sniffing the format."""
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    return parse_session_text(text, source=path)


def parse_session_text(text: str, source: str = "<text>") -> Session:
    if _looks_claude(text.splitlines()):
        msgs = messages_from_claude_jsonl(text)
        agent = "claude-code"
    else:
        msgs = messages_from_generic_jsonl(text)
        agent = "generic"
    return Session(source=source, messages=msgs, agent=agent)
