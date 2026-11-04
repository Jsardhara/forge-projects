"""wsaudit - per-tensor digests for model weight files (safetensors, GGUF).

Read-only, keyless, stdlib only. A digest that cannot be measured raises
WsAuditError; it never degrades into a clean result.
"""

__version__ = "1.0.0"
