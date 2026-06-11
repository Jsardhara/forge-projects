"""Custom exceptions for npm-shield."""


class NpmShieldError(Exception):
    """Base exception for npm-shield."""


class LockfileNotFoundError(NpmShieldError):
    """Raised when package-lock.json is not found at the given path."""


class InvalidLockfileError(NpmShieldError):
    """Raised when the lockfile is malformed or unrecognized."""
