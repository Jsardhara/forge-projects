"""AITokenProxy — Compress AI token usage by 50-80% via smart proxy.

A drop-in HTTP proxy that sits between AI coding tools (Claude Code, Cursor, Copilot)
and LLM APIs (OpenAI, Anthropic), automatically compressing prompts, tool outputs,
and RAG context before they hit the API.
"""

__version__ = "0.1.0"
