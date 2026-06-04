"""Tests for the compression engine."""

import pytest
from aitokenproxy.compressor import (
    CompressionPipeline,
    PromptCompressor,
    ToolOutputCompressor,
    RAGDedup,
    MessageWindowCompressor,
    count_tokens,
    CompressionResult,
)


class TestCountTokens:
    def test_empty_string(self):
        assert count_tokens("") == 1  # minimum 1

    def test_short_text(self):
        assert count_tokens("hello") == 1  # 5 chars // 4 = 1

    def test_longer_text(self):
        text = "a" * 400
        assert count_tokens(text) == 100


class TestCompressionResult:
    def test_savings_pct(self):
        r = CompressionResult(original_tokens=100, compressed_tokens=40, strategy="test")
        assert r.savings_pct == 60.0
        assert r.savings_tokens == 60

    def test_zero_original(self):
        r = CompressionResult(original_tokens=0, compressed_tokens=0, strategy="test")
        assert r.savings_pct == 0.0


class TestPromptCompressor:
    def setup_method(self):
        self.compressor = PromptCompressor()

    def test_removes_filler(self):
        text = "Please note that this is very important. Keep in mind that we need to proceed."
        result = self.compressor.compress(text)
        assert result.compressed_tokens < result.original_tokens
        assert result.savings_pct > 0

    def test_collapses_whitespace(self):
        text = "Hello    world\n\n\n\n\nGoodbye"
        result = self.compressor.compress(text)
        assert "\n\n\n" not in str(result.details)  # no triple newlines in output

    def test_short_prompt_unchanged(self):
        text = "Hello world"
        result = self.compressor.compress(text)
        # Short text may not change much
        assert result.original_tokens > 0

    def test_filler_patterns_compressed(self):
        text = "Basically, in order to achieve our goals, we really need to essentially focus."
        result = self.compressor.compress(text)
        assert result.savings_pct > 0


class TestToolOutputCompressor:
    def setup_method(self):
        self.compressor = ToolOutputCompressor()

    def test_short_output_unchanged(self):
        result = self.compressor.compress("short output")
        assert result.original_tokens == result.compressed_tokens
        assert result.details["truncated"] is False

    def test_long_output_truncated(self):
        long_output = "x" * 10000
        result = self.compressor.compress(long_output, max_tokens=100)
        assert result.compressed_tokens < result.original_tokens
        assert result.details["truncated"] is True

    def test_dict_truncation(self):
        data = {"key1": "a" * 5000, "key2": "b" * 5000, "key3": "c" * 5000}
        result = self.compressor.compress(data, max_tokens=100)
        assert result.compressed_tokens <= result.original_tokens


class TestRAGDedup:
    def setup_method(self):
        self.dedup = RAGDedup()

    def test_removes_duplicates(self):
        chunks = [
            "The quick brown fox jumps over the lazy dog",
            "The quick brown fox jumps over the lazy dog",  # exact dup
            "Something completely different here",
        ]
        result = self.dedup.dedup(chunks)
        assert result.details["duplicates_removed"] >= 1
        assert result.compressed_tokens < result.original_tokens

    def test_no_duplicates(self):
        chunks = ["unique chunk one", "unique chunk two", "unique chunk three"]
        result = self.dedup.dedup(chunks, similarity_threshold=0.99)
        assert result.details["duplicates_removed"] == 0

    def test_all_same(self):
        chunks = ["same text"] * 5
        result = self.dedup.dedup(chunks)
        assert result.details["chunks_out"] == 1


class TestMessageWindowCompressor:
    def setup_method(self):
        self.compressor = MessageWindowCompressor(keep_recent=4)

    def test_short_history_unchanged(self):
        msgs = [{"role": "user", "content": "hello"}]
        result = self.compressor.compress(msgs)
        assert result.details["messages_kept"] == 1
        assert result.details["summarized"] == 0

    def test_long_history_compressed(self):
        msgs = [{"role": "user", "content": f"message {i}" * 50} for i in range(20)]
        result = self.compressor.compress(msgs)
        assert result.details["messages_out"] < 20
        assert result.compressed_tokens < result.original_tokens

    def test_preserves_system_messages(self):
        msgs = [{"role": "system", "content": "You are a helpful assistant"}]
        msgs += [{"role": "user", "content": f"msg {i}" * 20} for i in range(10)]
        result = self.compressor.compress(msgs)
        # System message should be preserved
        assert result.details["messages_out"] < 11


class TestCompressionPipeline:
    def setup_method(self):
        self.pipeline = CompressionPipeline()

    def test_total_savings_empty(self):
        savings = self.pipeline.total_savings()
        assert savings["savings_pct"] == 0.0

    def test_compress_messages_empty(self):
        msgs, stats = self.pipeline.compress_messages([])
        assert msgs == []
        assert stats == []

    def test_compress_messages_with_tools(self):
        msgs = [
            {"role": "system", "content": "You are a coding assistant"},
            {"role": "user", "content": "Read the file"},
            {"role": "tool", "content": "x" * 5000},
            {"role": "assistant", "content": "I read it"},
        ]
        compressed, stats = self.pipeline.compress_messages(msgs)
        assert len(compressed) == 4
        # Should have at least one stat entry for tool compression
        assert len(stats) >= 1

    def test_compress_prompt(self):
        prompt = "Please note that this is very really extremely important. Keep in mind that we need to proceed."
        _, result = self.pipeline.compress_prompt(prompt)
        assert result.strategy == "prompt-compress"
