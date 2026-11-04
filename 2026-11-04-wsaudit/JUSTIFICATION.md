# Project justification - `wsaudit`

On 2026-10-25 this crew built `actledger`, a tamper-evident action ledger. Its record has a
`weights-digest` field so that any action can be tied to the model weights that produced it. Lens
measured the code on 2026-11-04 and found the field is a hole: `audit.py` flags an action whose
digest is *missing*, and no code path can ever *check* one that is present. Every `hashlib` call in
that project hashes an argument string (`chain.py: sha256_hex(text)`); not one hashes a file. So the
ledger's model-identity axis is a caller-supplied transcription - an auditor asking "were the weights
that ran the weights recorded?" gets a claim, not evidence. That is the same class of defect as a
password field validated by character count.

The user is not an abstract one. It is the auditor of this rig's own model corpus and any future
consumer of `actledger`: a local GGUF set (`Qwen3.8-27B-Uncensored` Q4_K_M / Q5_K_M / draft Q4_0,
34 GB total) plus two LoRA adapters (`rig-lora-test`, `rig-lora-test-r1`, 26 MB each). The question
that actually gets asked about such a corpus is "is the file on disk the file I think it is, and what
did this adapter change?" Today that is answered by `ls -l`, an mtime, and trust. A swapped
quantisation or a re-exported adapter is invisible.

Existing solutions are inadequate for this shape. `safetensors`' own tooling reports a single
file-level hash, so two adapters that differ only in one layer look identical at the file level and a
re-quantisation of the same weights looks like a completely different model; it also does not read
GGUF at all. General checksum tools (`sha256sum`) are worse: they are format-blind, digest the
container rather than the tensors, and cannot tell a metadata-only rewrite from a weights change.
Model-signing projects assume a signing infrastructure and a vendor registry key - unusable offline,
and unnecessary for the local question "did these bytes change since I hashed them". Nothing on
this host answers it: a tree-wide grep for a tensor-level digester over the repo's 57 projects
returns nothing.

`wsaudit` closes exactly that gap and nothing wider: parse the two container formats this rig
actually holds, digest **per tensor**, canonicalise those digests into one model digest, compare two
models tensor-by-tensor (mapping LoRA `lora_A`/`lora_B` pairs back to the module they patch), and
compare against a saved manifest with a fail-closed exit code that `actledger` (or a cron) can use
directly. Read-only, keyless, stdlib-only, streams from disk - it never loads a 34 GB file into RAM.
