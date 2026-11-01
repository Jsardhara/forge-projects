"""A deliberately small, deliberately tolerant SKILL.md frontmatter reader.

This is not a YAML parser and does not want to be one. The corpus it runs against is
hand-written by agents and humans alike, and the recorded lesson from this repo
(2026-10-24) is that a strict parser dies on real files while passing every tidy fixture.
So: read the three keys the ledger needs, ignore everything else, never raise, and report
*why* a file could not be read instead of pretending it was fine.
"""

from dataclasses import dataclass
from typing import Optional, Tuple

NAME = "name"
DESCRIPTION = "description"
TOOL_KEYS = ("tools", "allowed-tools", "allowed_tools", "allowedTools")


@dataclass(frozen=True)
class Frontmatter:
    name: Optional[str] = None
    description: str = ""
    tools: Tuple[str, ...] = ()
    ok: bool = False
    problem: str = "no-frontmatter"


def _unquote(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        inner = value[1:-1]
        if value[0] == "'":
            return inner.replace("''", "'")
        return inner.replace('\\"', '"')
    return value


def _split_inline_list(value):
    value = value.strip()
    if not (value.startswith("[") and value.endswith("]")):
        return None
    inner = value[1:-1].strip()
    if not inner:
        return ()
    return tuple(_unquote(item) for item in inner.split(",") if item.strip())


def _split_lines(text):
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def _body_lines(text):
    """Return the frontmatter body lines, or None with a problem name."""
    lines = _split_lines(text)
    while lines and not lines[0].strip():
        lines.pop(0)
    if not lines or lines[0].strip() != "---":
        return None, "no-frontmatter"
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return lines[1:index], ""
    return None, "unterminated-frontmatter"


def _top_level_entries(body):
    """Yield (key, value) for indent-0 `key: value` lines, skipping nested blocks."""
    entries = []
    for line in body:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[0] in " \t":
            continue  # nested or continuation: not a top-level key
        key, sep, value = line.partition(":")
        if not sep:
            continue
        entries.append((key.strip(), value.strip()))
    return entries


def _block_list(body, key):
    """Items of a block list belonging to top-level `key:`.

    An item is only accepted when it follows the key's own `key:` line and every line
    between is either blank or deeper-indented. A stray `- x` elsewhere is ignored, which
    is what keeps an orphan list item in a real file from corrupting the result.
    """
    items = []
    collecting = False
    for line in body:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if line[0] not in " \t":
            collecting = line.partition(":")[0].strip() == key and not line.partition(":")[2].strip()
            continue
        if not collecting:
            continue
        if stripped.startswith("- "):
            item = stripped[2:].strip()
            if ":" in item and not item.startswith(("[", "'", '"')):
                # `- path: scripts/x.py` is a mapping entry, not a tool name.
                continue
            items.append(_unquote(item))
        else:
            collecting = False
    return tuple(items)


def parse_frontmatter(text):
    """Parse the handful of keys the ledger needs. Never raises."""
    if not isinstance(text, str) or not text.strip():
        return Frontmatter(problem="no-frontmatter")
    body, problem = _body_lines(text)
    if body is None:
        return Frontmatter(problem=problem)

    name = None
    description = ""
    tools = ()
    for key, value in _top_level_entries(body):
        if key == NAME and name is None:
            name = _unquote(value) or None
        elif key == DESCRIPTION and not description:
            description = _unquote(value)
        elif key in TOOL_KEYS and not tools:
            inline = _split_inline_list(value)
            tools = inline if inline is not None else _block_list(body, key)

    if not name:
        return Frontmatter(name=None, description=description, tools=tools, problem="no-name")
    return Frontmatter(name=name, description=description, tools=tools, ok=True, problem="")
