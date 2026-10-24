"""Read what a package *claims* about its capabilities.

Three manifest forms actually ship in the plugin/skill marketplaces:
  * ``package.json``           -- npm-shaped plugins
  * ``plugin.json``            -- plugin manifests (also ``.claude-plugin/plugin.json``)
  * ``SKILL.md`` frontmatter   -- agent-skill packages

Only the first frontmatter block of a SKILL.md is read; capability keys appearing in
the body are prose, not a declaration.
"""

import json
import os
from dataclasses import dataclass

DECLARATION_KEYS = ("capabilities", "permissions", "requires_capabilities")

# capability -> accepted spellings. Everything is lowercased before lookup.
_ALIASES = {
    "network": ("network", "net", "network.egress", "net.egress", "net:egress",
                "egress", "http", "internet"),
    "shell": ("shell", "exec", "subprocess", "process", "shell.exec", "command"),
    "fs_write": ("fs_write", "filesystem", "fs", "fs:write", "fs.write", "file-write",
                 "filewrite", "write", "fs_write_access"),
    "credentials": ("credentials", "credential", "creds", "secrets", "secret",
                    "env", "environment"),
    "code_eval": ("code_eval", "code-eval", "eval", "dynamic-code", "dynamic_code"),
    "auto_hook": ("auto_hook", "auto-hook", "hooks", "hook", "autoexec", "auto_exec"),
}

KNOWN_CAPABILITIES = tuple(sorted(_ALIASES))


def normalize_capability(raw):
    """Map a manifest token onto a known capability, or return it lowercased."""
    token = str(raw).strip().lower()
    for capability, spellings in _ALIASES.items():
        if token in spellings:
            return capability
    return token


@dataclass(frozen=True)
class Declared:
    """What the package's manifests claim."""

    capabilities: tuple = ()
    hooks: tuple = ()
    sources: tuple = ()
    declares_capabilities: bool = False
    errors: tuple = ()

    @property
    def unknown(self):
        return tuple(c for c in self.capabilities if c not in KNOWN_CAPABILITIES)


def _read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _capabilities_from_json(payload):
    """Pull declared capability tokens out of a parsed manifest object."""
    found = []
    for key in DECLARATION_KEYS:
        value = payload.get(key)
        if value is None:
            continue
        if isinstance(value, dict):
            found.extend(value.keys())
        elif isinstance(value, (list, tuple)):
            found.extend(value)
        elif isinstance(value, str):
            found.append(value)
    return [normalize_capability(item) for item in found if str(item).strip()]


def _hooks_from_json(payload):
    scripts = payload.get("scripts")
    if not isinstance(scripts, dict):
        return []
    return [name for name in ("preinstall", "install", "postinstall")
            if str(scripts.get(name, "")).strip()]


def _parse_frontmatter(text):
    """Return the key/value mapping of the first YAML-ish frontmatter block."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    end = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end = index
            break
    if end is None:
        return None

    mapping = {}
    current = None
    current_indent = -1
    for raw in lines[1:end]:
        stripped = raw.lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(stripped)
        if stripped.startswith("- "):
            # A list item belongs to a key only when it is indented deeper than
            # that key and the key's value is a list. Anything else is a stray
            # line in a hand-written manifest -- tolerate it, never crash.
            existing = mapping.get(current) if current is not None else None
            if indent > current_indent and isinstance(existing, list):
                existing.append(stripped[2:].strip())
            continue
        if ":" not in raw:
            current = None
            current_indent = -1
            continue
        key, _, value = raw.partition(":")
        key = key.strip().lower()
        current = key
        current_indent = indent
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            mapping[key] = [part.strip() for part in inner.split(",") if part.strip()] if inner else []
        elif value:
            mapping[key] = value
        else:
            mapping[key] = []
    return mapping


def _capabilities_from_frontmatter(mapping):
    found = []
    for key in DECLARATION_KEYS:
        value = mapping.get(key)
        if isinstance(value, list):
            found.extend(value)
        elif isinstance(value, str) and value:
            found.append(value)
    return [normalize_capability(item) for item in found if str(item).strip()]


_CANDIDATES = ("package.json", "plugin.json", ".claude-plugin/plugin.json", "SKILL.md")


def load_declared(root):
    """Union the capability claims of every manifest found under ``root``."""
    capabilities, hooks, sources, errors = set(), set(), [], []
    declares_capabilities = False

    for relative in _CANDIDATES:
        path = os.path.join(root, relative)
        if not os.path.isfile(path):
            continue
        sources.append(relative)

        if relative.endswith(".md"):
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as handle:
                    mapping = _parse_frontmatter(handle.read())
            except OSError as exc:
                errors.append("%s: %s" % (relative, exc))
                continue
            if mapping is None:
                continue
            if any(key in mapping for key in DECLARATION_KEYS):
                declares_capabilities = True
            capabilities.update(_capabilities_from_frontmatter(mapping))
            continue

        try:
            payload = _read_json(path)
        except (OSError, ValueError) as exc:
            errors.append("%s: %s" % (relative, exc))
            continue
        if not isinstance(payload, dict):
            errors.append("%s: manifest is not a JSON object" % relative)
            continue
        if any(key in payload for key in DECLARATION_KEYS):
            declares_capabilities = True
        capabilities.update(_capabilities_from_json(payload))
        hooks.update(_hooks_from_json(payload))

    return Declared(
        capabilities=tuple(sorted(capabilities)),
        hooks=tuple(sorted(hooks)),
        sources=tuple(sources),
        declares_capabilities=declares_capabilities,
        errors=tuple(errors),
    )
