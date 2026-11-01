"""Static capability signals read from script bodies.

Nothing here executes anything. Each signal is a literal tool/API token, deliberately
narrow: a *word* like "network" or "secret" appearing in prose is not a capability, and a
detector that fires on prose is a detector that gets ignored. Where a token is ambiguous
(`eval(` on a model object, `open(` for reading) the pattern is anchored so the ambiguous
form does not match.
"""

import re
from dataclasses import dataclass
from typing import Tuple

# (signal id, capability, pattern). Order is report order, not match order.
SIGNALS = (
    # -- network -------------------------------------------------------------
    ("curl", "network", r"\bcurl\b"),
    ("wget", "network", r"\bwget\b"),
    ("python-urllib", "network", r"\burllib\.(?:request|urlopen)\b|from urllib import"),
    ("python-requests", "network", r"\brequests\.(?:get|post|put|patch|delete|head|request|Session)\b"),
    ("httpx", "network", r"\bhttpx\."),
    ("node-fetch", "network", r"(?<![\w.])fetch\s*\("),
    ("node-http", "network", r"require\(\s*['\"]https?['\"]\s*\)|from\s+['\"]https?['\"]"),
    ("socket", "network", r"\bsocket\.(?:socket|create_connection)\b"),
    ("http-client", "network", r"\bhttp\.client\b"),
    # -- subprocess / shell --------------------------------------------------
    ("subprocess", "exec", r"\bsubprocess\.(?:run|call|check_call|check_output|Popen)\b"),
    ("os-system", "exec", r"\bos\.system\s*\("),
    ("os-popen", "exec", r"\bos\.popen\s*\("),
    ("os-exec", "exec", r"\bos\.exec(?:v|ve|vp|vpe|l|le|lp|lpe)\b"),
    ("shell-dash-c", "exec", r"\b(?:ba|z|da)?sh\s+-c\b"),
    ("node-child-process", "exec", r"\bchild_process\b"),
    ("node-exec-sync", "exec", r"\b(?:execSync|spawnSync|execFileSync)\b"),
    ("python-pty", "exec", r"\bpty\.spawn\b"),
    # -- code evaluation -----------------------------------------------------
    ("eval", "code_eval", r"(?<![\w.])eval\s*\("),
    ("exec", "code_eval", r"(?<![\w.])exec\s*\("),
    ("new-function", "code_eval", r"\bnew\s+Function\s*\("),
    ("pickle-load", "code_eval", r"\bpickle\.loads?\s*\("),
    ("yaml-load", "code_eval", r"\byaml\.load\s*\("),
    ("node-vm", "code_eval", r"\bvm\.run(?:InNewContext|InThisContext|InContext)\b"),
    # -- filesystem writes ---------------------------------------------------
    ("write-text", "fs_write", r"\bwrite_(?:text|bytes)\s*\("),
    ("open-for-write", "fs_write", r"\bopen\s*\([^)\n]*['\"][wax]"),
    ("node-write", "fs_write", r"\b(?:writeFile|writeFileSync|appendFile)\s*\("),
    ("remove", "fs_write", r"\b(?:os\.remove|os\.unlink|os\.rmdir|unlinkSync)\b|\brmtree\s*\(|\bshutil\.rmtree\b"),
    ("copy-or-move", "fs_write", r"\bshutil\.(?:copy2?|copytree|move)\b"),
    ("mkdir", "fs_write", r"\bos\.makedirs\b|\bmkdirSync\s*\(|\bmkdir\s+-p\b"),
    # -- credentials ---------------------------------------------------------
    ("environ", "credentials", r"\bos\.environ\b"),
    ("getenv", "credentials", r"\b(?:os\.getenv|process\.env)\b"),
    ("dotenv", "credentials", r"\.env\b|\bload_dotenv\b|\bdotenv\b"),
    ("api-key", "credentials", r"\b[A-Z0-9_]*API_KEY\b|\bapi[_-]?key\b"),
    ("authorization", "credentials", r"\bAuthorization\b|\bBearer\b"),
    ("keyring", "credentials", r"\bkeyring\b|\bprivate_key\b|\bpassphrase\b"),
    # -- this host's agent surface ------------------------------------------
    ("hermes-home", "hermes_surface", r"\.hermes\b"),
    ("state-db", "hermes_surface", r"\bstate\.db\b"),
    ("profiles-dir", "hermes_surface", r"\bprofiles/"),
    ("memory-dir", "hermes_surface", r"\bmemory/"),
    ("vault", "hermes_surface", r"\bvault\b"),
)

_COMPILED = tuple((sid, cap, re.compile(pattern, re.MULTILINE)) for sid, cap, pattern in SIGNALS)

CAPABILITY_ORDER = ("network", "exec", "code_eval", "fs_write", "credentials", "hermes_surface")


@dataclass(frozen=True)
class Classification:
    capabilities: frozenset = frozenset()
    signals: Tuple[str, ...] = ()


def classify_text(text):
    """Return the capabilities and matched signal ids for a script body."""
    if not text:
        return Classification()
    capabilities = set()
    signals = set()
    for signal_id, capability, pattern in _COMPILED:
        if pattern.search(text):
            capabilities.add(capability)
            # Ids are namespaced by capability: `network:curl` cannot be confused with a
            # future `exec:curl-wrapper` the way a bare `curl` id could.
            signals.add("%s:%s" % (capability, signal_id))
    return Classification(capabilities=frozenset(capabilities), signals=tuple(sorted(signals)))


def classify_capabilities(text):
    return classify_text(text).capabilities
