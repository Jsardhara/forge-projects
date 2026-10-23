# Justification

**Problem.** On 2026-10-23 the LiteLLM 1.107.0 incident made a specific gap concrete: the
upstream GitHub source was clean, but every published wheel (PyPI, Docker, GHCR) carried a
backdoor that fired on any Python process start. Runtime. An agent sandbox such as
NVIDIA/OpenShell governs what a process may *do* once it is running; it does not answer the
prior question — **is this artifact the one upstream actually built?** Signature and
attestation verification (sigstore/cosign) answers "who signed it", and `pip --require-hashes`
answers "did I get the same bytes twice" — neither answers "do these bytes correspond to the
source I audited". That last hop is the one that was crossed.

**User.** A security engineer or CI owner who has audited a project's source and now wants to
refuse any distribution artifact that does not correspond to it — as a pre-install gate in CI
or pre-commit, with no network call and no trust in the package index.

**Why existing tools are inadequate here.** `pip` verifies nothing about source↔artifact
correspondence by design; `twine check` validates metadata only; SBOM tools inventory
dependencies rather than proving correspondence. Building generic code-audit tooling is also
the wrong move — that space is saturated (four plugin/skill marketplaces trending with zero
provenance the same week), which is exactly why this tool is narrow: one assertion,
`artifact == build(source)`, with a CI exit code.
