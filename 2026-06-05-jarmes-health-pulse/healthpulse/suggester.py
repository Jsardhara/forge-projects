"""Auto-fix suggester — maps known error patterns to fix suggestions."""

from __future__ import annotations


# Known error patterns and their fixes.
# Keys are substrings matched against error signatures.
KNOWN_FIXES: dict[str, str] = {
    "string_pattern_mismatch": (
        "Task status field uses a value not in the allowed pattern. "
        "Fix: Update tasks.json to use 'done' instead of 'completed', "
        "or update the Task model to accept 'completed' as a valid status."
    ),
    "ValidationError": (
        "Pydantic validation error — a data field doesn't match the expected schema. "
        "Fix: Check the input data format against the model definition. "
        "Look for type mismatches, missing required fields, or pattern violations."
    ),
    "ModuleNotFoundError": (
        "A Python module is missing. "
        "Fix: Install the missing package with 'uv pip install <package>' "
        "in the correct virtual environment."
    ),
    "ConnectionError": (
        "Network connection failed. "
        "Fix: Check network connectivity, API endpoint URLs, and firewall settings. "
        "If intermittent, add retry logic with exponential backoff."
    ),
    "timeout": (
        "A request timed out. "
        "Fix: Increase the timeout setting, check if the target service is running, "
        "or investigate network latency."
    ),
    "PermissionError": (
        "File or resource access denied. "
        "Fix: Check file permissions, ensure the process has access, "
        "and verify no other process has the file locked (common on Windows)."
    ),
    "FileNotFoundError": (
        "A required file was not found. "
        "Fix: Verify the file path, check if it was moved/deleted, "
        "and ensure the working directory is correct."
    ),
    "JSONDecodeError": (
        "Failed to parse JSON. "
        "Fix: Check the API response format, handle non-JSON responses gracefully, "
        "and validate JSON before parsing."
    ),
}


def get_suggestion(error_signature: str) -> str | None:
    """Get a fix suggestion for an error signature."""
    sig_lower = error_signature.lower()
    for pattern, fix in KNOWN_FIXES.items():
        if pattern.lower() in sig_lower:
            return fix
    return None
