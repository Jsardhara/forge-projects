"""The registry of verifiers this host actually has.

Discovery is by path convention, so a new verifier is picked up the day it lands.
Registration is what gives a verifier the extra arguments it needs to be useful in
an unattended run: a state path of its own, a tracked CVE id, and so on. An
unregistered verifier is still run (its bare module entry point), just marked
`known: False` in the report so a human knows nobody has blessed its default args.
"""

from dataclasses import dataclass, field
from typing import Tuple


@dataclass(frozen=True)
class VerifierSpec:
    name: str
    module: str
    path: str = ""
    args: Tuple[str, ...] = ()
    known: bool = False

    def expanded_args(self, state_dir: str, cve: str) -> Tuple[str, ...]:
        """Substitute the two tokens a registered verifier may use."""
        return tuple(
            a.replace("{state_dir}", state_dir).replace("{cve}", cve) for a in self.args
        )


#: Default args used on this host. Every entry is a read-only invocation; none of
#: them needs root, a key, or a write outside its own state file under {state_dir}.
DEFAULT_SPECS = {
    "secretsurface": VerifierSpec(
        name="secretsurface",
        module="secretsurface",
        args=(),
    ),
    "exitpath": VerifierSpec(
        name="exitpath",
        module="exitpath",
        args=(),
    ),
    "kcheck": VerifierSpec(
        name="kcheck",
        module="kcheck",
        args=(),
    ),
    "skillbom": VerifierSpec(
        name="skillbom",
        module="skillbom",
        args=("--ledger-out", "{state_dir}/skillbom-ledger.json"),
    ),
    "cvewatch": VerifierSpec(
        name="cvewatch",
        module="cvewatch",
        args=("--cve", "{cve}", "--state", "{state_dir}/cvewatch-{cve}.json"),
    ),
}


#: Per-verifier patterns for tokens that MOVE on every run without meaning
#: anything. A block height is a counter, not a verdict; without this the digest
#: flaps and every morning reports a transition that is not one.
VOLATILE = {
    "exitpath": (r"block \d+",),
}


def volatile_for(name: str) -> Tuple[str, ...]:
    return VOLATILE.get(name, ())


def spec_for(name: str, module: str, path: str) -> VerifierSpec:
    """Look the verifier up; fall back to a bare, unregistered spec."""
    base = DEFAULT_SPECS.get(name)
    if base is None:
        return VerifierSpec(name=name, module=module, path=path)
    return VerifierSpec(
        name=base.name, module=module, path=path, args=base.args, known=True
    )
