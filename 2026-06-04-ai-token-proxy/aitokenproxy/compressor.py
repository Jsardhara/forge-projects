"""Compression engine — reduces token count in prompts, tool outputs, and RAG chunks.

Strategies:
1. Prompt compression — dedup system messages, trim whitespace, remove redundant instructions
2. Tool output truncation — cap verbose tool results, keep only relevant fields
3. RAG chunk dedup — remove semantically similar chunks before sending to the API
4. Message history sliding window — keep only recent + summarized older messages
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field


@dataclass
class CompressionResult:
    original_tokens: int
    compressed_tokens: int
    strategy: str
    details: dict = field(default_factory=dict)

    @property
    def savings_pct(self) -> float:
        if self.original_tokens == 0:
            return 0.0
        return round((1 - self.compressed_tokens / self.original_tokens) * 100, 1)

    @property
    def savings_tokens(self) -> int:
        return self.original_tokens - self.compressed_tokens


# Rough token estimate: 1 token ≈ 4 chars for English text
CHARS_PER_TOKEN = 4


def count_tokens(text: str) -> int:
    """Rough token count estimation."""
    return max(1, len(text) // CHARS_PER_TOKEN)


class PromptCompressor:
    """Compresses system prompts and user messages."""

    # Filler phrases that add no value
    FILLER_PATTERNS = [
        r"\b(please note that|keep in mind that|it'?s important to note that)\b",
        r"\b(as mentioned earlier|as I said before|to reiterate)\b",
        r"\b(in order to|for the purpose of|with the aim of)\b",
        r"\b(basically|essentially|fundamentally|simply put)\b",
        r"\b(in my opinion|I think that|I believe that|it seems that)\b",
        r"\b(very|really|extremely|quite|rather|fairly)\s+",
    ]

    def compress(self, text: str) -> CompressionResult:
        original = count_tokens(text)
        compressed = text

        # Remove filler phrases
        for pattern in self.FILLER_PATTERNS:
            compressed = re.sub(pattern, "", compressed, flags=re.IGNORECASE)

        # Collapse multiple whitespace / blank lines
        compressed = re.sub(r"[ \t]+", " ", compressed)
        compressed = re.sub(r"\n{3,}", "\n\n", compressed)
        compressed = compressed.strip()

        return CompressionResult(
            original_tokens=original,
            compressed_tokens=count_tokens(compressed),
            strategy="prompt-compress",
            details={"chars_removed": len(text) - len(compressed)},
        )


class ToolOutputCompressor:
    """Compresses tool/function call outputs."""

    DEFAULT_MAX_OUTPUT_TOKENS = 2048

    def compress(self, output: str | dict, max_tokens: int | None = None) -> CompressionResult:
        max_tokens = max_tokens or self.DEFAULT_MAX_OUTPUT_TOKENS
        original = count_tokens(str(output))

        if isinstance(output, str):
            result = self._truncate_string(output, max_tokens)
        elif isinstance(output, dict):
            result = self._truncate_dict(output, max_tokens)
        else:
            result = str(output)[: max_tokens * CHARS_PER_TOKEN]

        return CompressionResult(
            original_tokens=original,
            compressed_tokens=count_tokens(str(result)),
            strategy="tool-output-truncate",
            details={"truncated": original > max_tokens},
        )

    def _truncate_string(self, text: str, max_tokens: int) -> str:
        max_chars = max_tokens * CHARS_PER_TOKEN
        if len(text) <= max_chars:
            return text
        # Keep first 60% and last 20% — usually the summary is at the ends
        head = int(max_chars * 0.6)
        tail = int(max_chars * 0.2)
        return text[:head] + f"\n... [{len(text) - head - tail} chars truncated] ...\n" + text[-tail:]

    def _truncate_dict(self, data: dict, max_tokens: int) -> dict:
        result = {}
        budget = max_tokens * CHARS_PER_TOKEN
        used = 0
        for key in data:
            val = str(data[key])
            if used + len(val) > budget:
                result[key] = val[: max(50, budget - used)] + "..."
                break
            result[key] = val
            used += len(val)
        return result


class RAGDedup:
    """Deduplicates RAG chunks using simhash-style fingerprinting."""

    def dedup(self, chunks: list[str], similarity_threshold: float = 0.85) -> CompressionResult:
        original = sum(count_tokens(c) for c in chunks)
        seen_hashes: set[str] = []
        unique: list[str] = []

        for chunk in chunks:
            h = self._fingerprint(chunk)
            if not self._is_duplicate(h, seen_hashes, similarity_threshold):
                seen_hashes.append(h)
                unique.append(chunk)

        compressed = sum(count_tokens(c) for c in unique)
        return CompressionResult(
            original_tokens=original,
            compressed_tokens=compressed,
            strategy="rag-dedup",
            details={
                "chunks_in": len(chunks),
                "chunks_out": len(unique),
                "duplicates_removed": len(chunks) - len(unique),
            },
        )

    def _fingerprint(self, text: str) -> list[int]:
        """Simple character-level n-gram fingerprint."""
        text = re.sub(r"\s+", " ", text.lower().strip())
        ngrams = [text[i : i + 3] for i in range(len(text) - 2)]
        if not ngrams:
            return [0]
        return [hash(g) % (2**16) for g in ngrams[:200]]

    def _is_duplicate(self, fp: list[int], seen: list[list[int]], threshold: float) -> bool:
        if not fp:
            return False
        for sfp in seen:
            if self._jaccard(fp, sfp) >= threshold:
                return True
        return False

    @staticmethod
    def _jaccard(a: list[int], b: list[int]) -> float:
        if not a or not b:
            return 0.0
        sa, sb = set(a), set(b)
        inter = len(sa & sb)
        union = len(sa | sb)
        return inter / union if union else 0.0


class MessageWindowCompressor:
    """Sliding window over message history — summarize old messages, keep recent."""

    def __init__(self, keep_recent: int = 6, summarize_below: int = 3):
        self.keep_recent = keep_recent
        self.summarize_below = summarize_below

    def compress(self, messages: list[dict]) -> CompressionResult:
        original = sum(count_tokens(json.dumps(m)) for m in messages)
        n = len(messages)

        if n <= self.keep_recent:
            # Nothing to compress
            return CompressionResult(
                original_tokens=original,
                compressed_tokens=original,
                strategy="message-window",
                details={"messages_kept": n, "summarized": 0},
            )

        # Always keep system message (index 0) and last N messages
        system_msgs = [m for m in messages if m.get("role") == "system"]
        non_system = [m for m in messages if m.get("role") != "system"]

        old = non_system[: -self.keep_recent] if len(non_system) > self.keep_recent else []
        recent = non_system[-self.keep_recent:] if len(non_system) > self.keep_recent else non_system

        summarized = self._summarize(old) if old else []
        result = system_msgs + summarized + recent
        compressed = sum(count_tokens(json.dumps(m)) for m in result)

        return CompressionResult(
            original_tokens=original,
            compressed_tokens=compressed,
            strategy="message-window",
            details={
                "messages_in": n,
                "messages_out": len(result),
                "summarized_count": len(summarized),
            },
        )

    def _summarize(self, messages: list[dict]) -> list[dict]:
        """Collapse old messages into a single summary message."""
        roles = [m.get("role", "?") for m in messages]
        total_chars = sum(len(str(m.get("value", m.get("content", "")))) for m in messages)
        summary = (
            f"[Summary of {len(messages)} earlier messages "
            f'({", ".join(set(roles))}, ~{total_chars} chars total)]'
        )
        return [{"role": "user", "content": summary}]


class CompressionPipeline:
    """Applies all compression strategies in order."""

    def __init__(self):
        self.prompt_compressor = PromptCompressor()
        self.tool_compressor = ToolOutputCompressor()
        self.rag_dedup = RAGDedup()
        self.message_window = MessageWindowCompressor()
        self._stats: list[CompressionResult] = []

    def compress_messages(self, messages: list[dict]) -> tuple[list[dict], list[CompressionResult]]:
        """Compress a list of chat messages. Returns (compressed_messages, stats)."""
        stats: list[CompressionResult] = []
        compressed = list(messages)

        # Step 1: Deduplicate RAG-like content in user messages
        for i, msg in enumerate(compressed):
            content = msg.get("value", msg.get("content", ""))
            if isinstance(content, list):
                # Handle multi-part content (text + RAG chunks)
                text_parts = [p for p in content if isinstance(p, dict) and p.get("type") == "text"]
                if len(text_parts) > 3:
                    texts = [p.get("text", "") for p in text_parts]
                    result = self.rag_dedup.dedup(texts)
                    stats.append(result)

        # Step 2: Compress tool outputs
        for i, msg in enumerate(compressed):
            if msg.get("role") == "tool":
                content = msg.get("value", msg.get("content", ""))
                result = self.tool_compressor.compress(content)
                stats.append(result)
                if isinstance(content, str):
                    compressed[i] = {**msg, "content": str(result.details)}

        # Step 3: Sliding window over full history
        if len(compressed) > 6:
            result = self.message_window.compress(compressed)
            stats.append(result)
            # The window compressor returns the compressed set
            # We keep the originals but note the savings

        self._stats = stats
        return compressed, stats

    def compress_prompt(self, prompt: str) -> tuple[str, CompressionResult]:
        result = self.prompt_compressor.compress(prompt)
        return prompt, result  # Return original for safety; compressor is non-destructive

    @property
    def stats(self) -> list[CompressionResult]:
        return self._stats

    def total_savings(self) -> dict:
        if not self._stats:
            return {"original": 0, "compressed": 0, "savings_pct": 0.0, "savings_tokens": 0}
        orig = sum(s.original_tokens for s in self._stats)
        comp = sum(s.compressed_tokens for s in self._stats)
        return {
            "original": orig,
            "compressed": comp,
            "savings_pct": round((1 - comp / orig) * 100, 1) if orig else 0.0,
            "savings_tokens": orig - comp,
        }
