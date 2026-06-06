"""Data models for AI failure modes."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class Severity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Category(str, enum.Enum):
    HALLUCINATION = "hallucination"
    INSTRUCTION_FOLLOWING = "instruction_following"
    CONTEXT_WINDOW = "context_window"
    SAFETY_REFUSAL = "safety_refusal"
    TOOL_USE = "tool_use"
    REASONING = "reasoning"
    CODE_GENERATION = "code_generation"
    PROMPT_INJECTION = "prompt_injection"
    COST_TOKEN = "cost_token"
    LATENCY = "latency"
    DATA_LEAK = "data_leak"
    OTHER = "other"


class FailureMode(BaseModel):
    """A single documented AI failure mode."""
    vid: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=10)
    severity: Severity = Severity.MEDIUM
    category: Category = Category.OTHER
    model: Optional[str] = Field(None, description="AI model that exhibited the failure")
    prompt_excerpt: Optional[str] = Field(None, max_length=2000, description="What was asked (sanitized)")
    expected_behavior: Optional[str] = None
    actual_behavior: Optional[str] = None
    workaround: Optional[str] = None
    source_url: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    upvotes: int = 0
    verified: bool = False


class FailureModeCreate(BaseModel):
    """Input for creating a new failure mode."""
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=10)
    severity: Severity = Severity.MEDIUM
    category: Category = Category.OTHER
    model: Optional[str] = None
    prompt_excerpt: Optional[str] = Field(None, max_length=2000)
    expected_behavior: Optional[str] = None
    actual_behavior: Optional[str] = None
    workaround: Optional[str] = None
    source_url: Optional[str] = None
    tags: list[str] = Field(default_factory=list)


class FailureModeUpdate(BaseModel):
    """Input for updating an existing failure mode."""
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None, min_length=10)
    severity: Optional[Severity] = None
    category: Optional[Category] = None
    model: Optional[str] = None
    prompt_excerpt: Optional[str] = Field(None, max_length=2000)
    expected_behavior: Optional[str] = None
    actual_behavior: Optional[str] = None
    workaround: Optional[str] = None
    source_url: Optional[str] = None
    tags: Optional[list[str]] = None
    verified: Optional[bool] = None


class SearchQuery(BaseModel):
    """Search parameters for failure modes."""
    q: Optional[str] = None
    category: Optional[Category] = None
    severity: Optional[Severity] = None
    model: Optional[str] = None
    tag: Optional[str] = None
    verified_only: bool = False
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)


class SearchResult(BaseModel):
    """Paginated search results."""
    total: int
    items: list[FailureMode]
    limit: int
    offset: int


class Stats(BaseModel):
    """Aggregate statistics about the failure database."""
    total_entries: int
    by_severity: dict[str, int]
    by_category: dict[str, int]
    by_model: dict[str, int]
    verified_count: int
    top_tags: list[tuple[str, int]]
