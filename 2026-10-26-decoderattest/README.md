# decoderattest

**Your lockfile says you're patched. Your runtime says which decoder you actually loaded.**

`decoderattest` answers one question about CVE-2026-111497 ("Broccoli2Shell"), the
out-of-bounds write in Google's reference Brotli **C decoder**:

> Which Brotli decoder is loaded, on this machine, right now?

It is a local runtime inventory and a rule check, not a vulnerability scanner, not an
SBOM generator, and it makes no network calls.

## Why this exists

The advisory says it better than a pitch can:

- *"Express and body-parser don't contain the bug. They're just paths to it, so
  upgrading them won't help."*
- *"Node.js bundles its own copy of Brotli, which means the system `libbrotli` doesn't
  matter there. Only the Node.js version does."*
- *"Don't wait for your scanner. When this was disclosed, pip-audit, Dependabot and
  Safety didn't reliably flag the affected PyPI versions. The CVE record named the
  upstream Google repository, not the PyPI packages."*

So the exposure question is not a manifest question. It is which binary is installed,
which C-compiled wheel is importable **in each interpreter**, and which system library
a process links.

## Run it

No install, no dependencies, standard library only:

```sh
cd 2026-10-26-decoderattest
PYTHONPATH=src python3 -m decoderattest
```

Point it at a build tree to catch vendored copies, and at a specific interpreter:

```sh
PYTHONPATH=src python3 -m decoderattest \
  --scan-vendor ~/src/mytool \
  --python /usr/bin/python3.12 \
  --json
```

Exit codes are the contract:

| exit | meaning |
|------|---------|
| 0 | nothing at or above the `--fail-on` threshold (default: `exposed`) |
| 1 | at or above the threshold |
| 2 | **could not answer** — unreadable rule file, missing vendor path, broken probe |

`2` is not noise. A gate that returns 0 because it could not read its own rule file is
the silent-death failure mode this tool exists to prevent.

## What it checks

| source | how it is determined | why it matters |
|--------|----------------------|----------------|
| Node.js | every `node`/`nodejs` on `PATH`, asked for `--version` | bundles its own decoder; the system library is irrelevant |
| Python wheels | each interpreter gets a one-line probe in **its own process**, reporting the importable `Brotli` / `brotlicffi` version (falling back to distribution metadata) | a wheel in *another* venv cannot be imported by this one |
| system library | `dpkg-query` (then `rpm`) for `libbrotli1` / `libbrotlidec1` / `brotli` | dynamically linked programs stay vulnerable until the package updates **and** the process restarts |
| vendored copies | walks a directory you pass with `--scan-vendor`, finds `brotli/decode.h` | a distribution update fixes nothing for a private copy |

### The vendored case uses two independent signals

1. the declared version macros in `common/version.h`;
2. the `BLOCK_SWITCH` error code (`-17`) that the fix introduced in `decode.h`.

If a copy claims `1.2.1` but has no `BLOCK_SWITCH`, the signals disagree and the copy is
reported **UNKNOWN**, not patched. A certification of safety that cannot be shown to be
true is the failure mode this tool is built to avoid.

## Rule file

`src/decoderattest/data/brotli-decoder.json` is data, not code: an advisory identity and
one entry per affected product. Two evaluation kinds:

- `range` — a package with a version span and a list of published fixes. The `fixed`
  list wins inside the span, because `1.1.1` sits numerically inside `1.0.3 - 1.2.0`
  while being a fix, not a victim.
- `runtime_lines` — a runtime with per-major support lines (Node.js). A line named in
  the file is affected below its fix; an **older** line not named in the file is
  end-of-life with no fix; a **newer** line not named in the file is UNKNOWN, because
  this rule file cannot attest a release it has never seen.

Nothing is guessed. Anything the evaluator cannot place returns `unknown`.

## Real output on the machine this was built on

```
decoderattest - CVE-2026-111497 (GHSA-9v8h-qqgm-4m35 / PYSEC-2026-4322)
------------------------------------------------------------------------------
VERDICT: EXPOSED
------------------------------------------------------------------------------
CRITICAL node      /home/jyot/.hermes/node/bin/node         26.8.2         affected
         line 26 is affected below 26.12.1
         fix: 26.12.1
CRITICAL vendored  ...rotli-1.2.0/c/include/brotli/decode.h 1.2.0          affected
CRITICAL system    libbrotli1                               1.2.0-3build1  affected
OK       vendored  ...rotli-1.2.1/c/include/brotli/decode.h 1.2.1          patched
------------------------------------------------------------------------------
counts: found 6 | affected 5 | patched 1 | unknown 0
note: python: 4 python interpreter(s) probed, 0 with a Brotli binding importable
      (a clean Python branch means nothing was linked, not that it was patched)
```

The last note is deliberate: a branch that found nothing says so, because silence in a
report reads as "fine" and that is how a real exposure gets missed.

## Tests

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

94 tests, standard library only. Coverage measured with stdlib `trace`: 744/744
executable lines across the seven logic modules.

## Limits, stated plainly

- The rule file is as current as its last edit; it does not update itself. A new
  advisory needs a new rule entry.
- Vendored discovery only finds copies with a `brotli/` directory holding `decode.h`.
  A decoder vendored under a renamed directory, or a statically linked binary with
  stripped symbols, is invisible here.
- Python coverage is limited to importable `Brotli` / `brotlicffi`. A binding built
  into a PyInstaller bundle or a compiled extension with a different name is not seen.
- Node's bundled decoder is attested from the runtime version. If a build replaces it
  with a newer library, this tool will still report the version's default.
