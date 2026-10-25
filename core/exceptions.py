"""Custom domain exceptions for AegisGate Core.

Strictly follows python_clean_code.md custom exception handling standards.
"""

from typing import Any


class AegisGateBaseError(Exception):
    """Base exception for all AegisGate errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message: str = message
        self.details: dict[str, Any] = details or {}


class PluginNotFoundError(AegisGateBaseError):
    """Raised when a requested plugin cannot be found or is not registered."""


class PluginProcessError(AegisGateBaseError):
    """Raised when a plugin child process fails to start, crashes, or produces invalid output."""


class PluginExecutionError(AegisGateBaseError):
    """Raised when a plugin encounters a runtime error during query execution."""


class ExecutionTimeoutError(AegisGateBaseError):
    """Raised when a query execution exceeds the strict 15s/30s timeout guard."""


class RuleViolationError(AegisGateBaseError):
    """Raised when an AI query violates active governance rules (e.g. forbidden join, table scan)."""


class ExecutionStateError(AegisGateBaseError):
    """Raised when an invalid state transition is attempted in the State Machine."""


class StorageError(AegisGateBaseError):
    """Raised when an error occurs during reading or writing to SQLite or Knowledge Docs."""


class JsonRpcProtocolError(AegisGateBaseError):
    """Raised when a JSON-RPC message is malformed or returns an RPC error response."""
