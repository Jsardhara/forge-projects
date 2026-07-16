"""Synthetic transcript builders for tests.

These produce Claude-Code-shaped JSONL strings (and generic ones) so the parsers
can be exercised without real agent session files. They are NOT real user data.
"""
import json


def claude_line(role, usage, model=None, content=None, mtype=None):
    msg = {"role": role}
    if content is not None:
        msg["content"] = content
    if usage is not None:
        msg["usage"] = usage
    if model is not None:
        msg["model"] = model
    obj = {"type": mtype or role, "message": msg}
    return json.dumps(obj)


def assistant_text(text):
    return [{"type": "text", "text": text}]


def tool_use_read(path):
    return [{"type": "tool_use", "name": "Read", "input": {"file_path": path}}]


def tool_result(content):
    return [{"type": "tool_result", "content": content}]


def claude_session_jsonl(lines):
    return "\n".join(lines) + "\n"


def generic_line(role, prompt_tokens, completion_tokens, model=None):
    obj = {
        "role": role,
        "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens},
    }
    if model:
        obj["model"] = model
    return json.dumps(obj)
