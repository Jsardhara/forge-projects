# pubgate — Published-Artifact Provenance Gate

Answer one question before `pip install`: **is this artifact the one built from the source
I audited?** Offline, all-stdlib, zero external dependencies, CI exit code.

Built from Lens Intel 2026-10-23 — the LiteLLM 1.107.0 incident, where upstream GitHub
source was clean but every published wheel (PyPI, Docker, GHCR) carried a backdoor that
fired on any Python process start. Runtime sandboxes govern what a process may *do*; they
do not answer this question. Signatures answer "who signed it", `--require-hashes` answers
"did I get the same bytes twice". Neither answers "do these bytes correspond to the source".

## The two checks

| Check | Question | Catches |
|---|---|---|
| `RECORD` integrity | Does every member match the digest the build recorded? | post-build tampering, unlisted extra files |
| source correspondence | Does every audited source file appear byte-identical? | **clean source, poisoned artifact** (attacker controls the build, so RECORD alone is not enough) |

## Usage

```bash
# 1. Hash the source tree you actually reviewed (once, at audit time)
pubgate record --source ./litellm-src --name litellm --version 1.107.0 --out litellm.manifest.json

# 2. Gate every artifact before install / in CI
pubgate verify --wheel litellm-1.107.0-py3-none-any.whl --manifest litellm.manifest.json
```

Exit codes — fail closed:

| code | meaning |
|---|---|
| `0` | PASS — artifact corresponds to the audited source |
| `1` | FAIL — violations listed (see below) |
| `2` | unusable input (missing file, not a zip, bad manifest) — never a silent pass |

Violation kinds: `RECORD_MISMATCH`, `RECORD_UNLISTED`, `RECORD_MISSING`,
`SOURCE_MISMATCH`, `SOURCE_ABSENT`, `VERSION_MISMATCH`.

`verify` without `--manifest` says so out loud: the artifact is self-consistent but **NOT**
proven to correspond to any audited source, and it prints `SOURCE SKIPPED`.

## Proven on real artifacts

Real PyPI wheel + its real sdist, not just fixtures:

```
$ pubgate verify --wheel six-1.17.0-py2.py3-none-any.whl --manifest six.manifest.json
RECORD PASS: 0
SOURCE PASS: 0
PASS six-1.17.0-py2.py3-none-any.whl (0 violations)          # exit 0

$ pubgate verify --wheel six-evil.whl --manifest six.manifest.json   # one module swapped
RECORD FAIL: 1
  - RECORD_MISMATCH six.py — RECORD says c51c91f703d3…, artifact is b3fbd34a3952…
SOURCE FAIL: 1
  - SOURCE_MISMATCH six.py — artifact content b3fbd34a3952… != audited source c51c91f703d3
FAIL six-evil.whl (2 violations)                             # exit 1
```

## Install / test

```bash
pip install .            # provides the `pubgate` command
python3 -m unittest discover -s tests    # 18 tests, stdlib only (no pytest needed)
```

## Scope, deliberately narrow

Does **not** verify signatures or attestations — that is sigstore/cosign's job, and
composing the two is the point. Does **not** audit code for vulnerabilities: four plugin
and skill marketplaces were trending with zero provenance the same week, and another
code-audit scanner is not the gap. This tool makes exactly one assertion, verifiably.
