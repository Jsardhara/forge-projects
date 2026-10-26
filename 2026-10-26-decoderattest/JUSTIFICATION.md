# Project Justification — decoderattest

CVE-2026-111497 ("Broccoli2Shell") is an out-of-bounds write in Google's reference
Brotli **C decoder** reaching Node.js (bundled copy), Python `Brotli` / `brotlicffi`
wheels, and any program that links the system `libbrotli`. It is triggerable by
compressed data the process did not choose to trust: a fetched HTTP response, a
webhook body, an `import from URL` path. The advisory's own text names the reason a
new tool is needed: *"Don't wait for your scanner. When this was disclosed, pip-audit,
Dependabot and Safety didn't reliably flag the affected PyPI versions. The CVE record
named the upstream Google repository, not the PyPI packages."* And, for the biggest
class of installs: *"Express and body-parser don't contain the bug. They're just paths
to it, so upgrading them won't help."*

The user is anyone who owns a machine or an image and has to answer one question
honestly: **which Brotli decoder is actually loaded at runtime, here, right now?**
Existing tooling answers adjacent questions and misses this one. SCA/lockfile scanners
(`pip-audit`, Dependabot, `npm audit`, Safety) read a manifest and an advisory feed —
they cannot see a Node binary's bundled decoder, a vendored `brotli/decode.h` inside a
build tree, or a system library that a distribution has not patched, and they were
demonstrably wrong about this CVE on disclosure day. SBOM generators (syft, CycloneDX)
inventory declared components; a statically linked or vendored copy is not a declared
component, and a non-empty SBOM is not a verdict. Runtime/EDR agents report process
behaviour, not which decompressor version a binary linked.

`decoderattest` is deliberately narrow. It enumerates the decoder surface on the
machine it runs on — Node binaries and their version, each reachable Python
interpreter and the Brotli bindings importable in *that* interpreter, the packaged
system Brotli library, and any vendored `brotli/` source tree the caller points it at
— and attests each one against a versioned rule file, with two independent signals for
the vendored case (declared version macros and the `BLOCK_SWITCH` error code the fix
introduced). It does not generate an SBOM, does not scan a network, and is not a
general CVE database: a scanner that has to be right about everything is how this one
gets missed. It answers a question that is local, deterministic, and checkable in one
command, and it says "unknown" out loud when it cannot prove either answer — because a
confident wrong verdict is worse than no tool at all.
