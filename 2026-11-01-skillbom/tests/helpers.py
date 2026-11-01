"""Fixture builders for the skillbom tests.

Everything is written to a caller-supplied temp directory; nothing here touches the
real host, and no fixture is allowed to depend on the machine it runs on.
"""

import hashlib
import os

from skillbom.models import Root


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def write(path, text):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return path


def skill_md(name, description="A skill.", tools=None, extra=""):
    lines = ["---", "name: %s" % name, 'description: "%s"' % description]
    if tools is not None:
        lines.append("tools: [%s]" % ", ".join(tools))
    lines.extend(["---", "", "# %s" % name, ""])
    return "\n".join(lines) + extra


def make_skill(root, rel, name, scripts=None, tools=None, extra="", description="A skill."):
    """Create one skill directory under `root` and return its path."""
    path = os.path.join(root, rel)
    write(os.path.join(path, "SKILL.md"), skill_md(name, description, tools, extra))
    for rel_path, content in (scripts or {}).items():
        write(os.path.join(path, rel_path), content)
    return path


def make_root(base, label, kind="profile"):
    return Root(label=label, path=os.path.join(base, label), kind=kind)


def make_profile(base, label, skills):
    """skills: mapping of rel -> dict(name=..., scripts=..., ...)"""
    root = make_root(base, label)
    for rel, kwargs in skills.items():
        make_skill(root.path, rel, **kwargs)
    return root
