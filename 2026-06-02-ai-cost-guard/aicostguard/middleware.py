"""Middleware for tracking AI API usage via interceptors."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Optional

from aicostguard.pricing import estimate_cost
from aicostguard.tracker import UsageRecord, UsageTracker


class OpenAIInterceptor:
    """Wrap OpenAI client calls to automatically track usage."""

    def __init__(self, client: Any, tracker: Optional[UsageTracker] = None, team_id: str = "default"):
        self._client = client
        self._tracker = tracker or UsageTracker()
        self._team_id = team_id

    def _extract_usage(self, response: Any) -> tuple[int, int]:
        """Extract token usage from an OpenAI response."""
        try:
            usage = getattr(response, "usage", None)
            if usage is None and isinstance(response, dict):
                usage = response.get("usage", {})
            if usage is None:
                return 0, 0
            if isinstance(usage, dict):
                return usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)
            return getattr(usage, "prompt_tokens", 0), getattr(usage, "completion_tokens", 0)
        except Exception:
            return 0, 0

    def _extract_model(self, response: Any) -> str:
        try:
            if isinstance(response, dict):
                return response.get("model", "unknown")
            return getattr(response, "model", "unknown")
        except Exception:
            return "unknown"

    def chat_completions_create(self, model: str, messages: list, **kwargs) -> Any:
        """Intercept chat.completions.create."""
        response = self._client.chat.completions.create(model=model, messages=messages, **kwargs)
        in_tokens, out_tokens = self._extract_usage(response)
        actual_model = self._extract_model(response)
        cost = estimate_cost("openai", actual_model, in_tokens, out_tokens)
        self._tracker.record_usage(UsageRecord(
            provider="openai",
            model=actual_model,
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            estimated_cost=cost,
            team_id=self._team_id,
        ))
        return response


class AnthropicInterceptor:
    """Wrap Anthropic client calls to automatically track usage."""

    def __init__(self, client: Any, tracker: Optional[UsageTracker] = None, team_id: str = "default"):
        self._client = client
        self._tracker = tracker or UsageTracker()
        self._team_id = team_id

    def _extract_usage(self, response: Any) -> tuple[int, int]:
        try:
            usage = getattr(response, "usage", None)
            if usage is None and isinstance(response, dict):
                usage = response.get("usage", {})
            if usage is None:
                return 0, 0
            if isinstance(usage, dict):
                return usage.get("input_tokens", 0), usage.get("output_tokens", 0)
            return getattr(usage, "input_tokens", 0), getattr(usage, "output_tokens", 0)
        except Exception:
            return 0, 0

    def messages_create(self, model: str, messages: list, max_tokens: int = 1024, **kwargs) -> Any:
        response = self._client.messages.create(model=model, messages=messages, max_tokens=max_tokens, **kwargs)
        in_tokens, out_tokens = self._extract_usage(response)
        cost = estimate_cost("anthropic", model, in_tokens, out_tokens)
        self._tracker.record_usage(UsageRecord(
            provider="anthropic",
            model=model,
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            estimated_cost=cost,
            team_id=self._team_id,
        ))
        return response


class CostGuardMiddleware:
    """Generic middleware that can wrap any AI API call."""

    def __init__(self, tracker: Optional[UsageTracker] = None, team_id: str = "default"):
        self._tracker = tracker or UsageTracker()
        self._team_id = team_id

    def track(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        tags: str = "",
    ) -> float:
        """Manually track a usage event. Returns estimated cost."""
        cost = estimate_cost(provider, model, input_tokens, output_tokens)
        self._tracker.record_usage(UsageRecord(
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost=cost,
            team_id=self._team_id,
            tags=tags,
        ))
        return cost
