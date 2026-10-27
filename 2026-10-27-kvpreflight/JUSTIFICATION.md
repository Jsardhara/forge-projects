# Project Justification — kvpreflight

On 2026-08-27 Cloudflare deployed GLM-5.3 on Workers AI advertising a 1,048,576-token
context window while the prefill KV pool it had actually allocated held only 681,280
tokens. Their published post-mortem states the mismatch was known before launch and
deliberately assumed safe: *"We expected the engine to return an error for any prompt
it could not process."* The engine did not. In disaggregated prefill/decode mode the
over-length prompt was rejected, a one-token placeholder was prefilled instead, and the
decode node attended over stale cache pages belonging to other tenants — 155 responses
leaked cross-tenant data over two weeks, reproducible in 25 minutes with two accounts.
The remediation post names the durable problem itself: *"Relying on pool size alone is
fragile: any change to quantization, tensor parallelism, CUDA graph sizes, or a future
model version changes the pool size in a way that's easy to miss."*

The user is anyone operating a self-hosted inference server — vLLM, SGLang, TGI,
TensorRT-LLM — who sets `--max-model-len` in a launch script or a Helm values file and
believes the advertised context is the context that exists. The arithmetic that
connects them (`2 x kv_heads x head_dim x dtype_bytes x layers` per token, sharded by
tensor parallelism, rounded down to KV blocks, then compared against the budget left
after weights) is never checked in CI, is not a vulnerability-database lookup, and
silently changes when someone flips an AWQ checkpoint or bumps `--tensor-parallel-size`.

Existing solutions are inadequate because they answer a different question. Vulnerability
scanners (Trivy, pip-audit, SkillSpector) only speak about known CVEs, and this failure
was a misconfiguration, not a CVE in the deployed version. GPU capacity planners report
whether a model *fits*, not whether the *context* fits. vLLM's own startup log prints a
KV pool size in blocks, which requires the operator to already know bytes-per-token to
interpret, and prints nothing at all when the server is defined in a manifest that is
never launched locally.

kvpreflight answers one question with one number: **does the KV pool this configuration
implies actually hold the context length it advertises?** It is offline, stdlib-only,
reads the model's real `config.json`, and — critically — is allowed to answer UNKNOWN.
Cloudflare's failure was an assumption that something else would error out; a preflight
that guesses PASS would reproduce it.
