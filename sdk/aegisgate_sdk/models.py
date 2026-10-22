"""AegisGate Plugin SDK - Models and Typed Contracts."""

from dataclasses import dataclass, field
from typing import Any


class PluginException(Exception):
    """Base exception for all plugin errors."""
    def __init__(self, message: str, code: int = -32603, data: Any | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.data = data


class PluginConfigError(PluginException):
    """Raised when connection configuration parameters are invalid."""
    def __init__(self, message: str) -> None:
        super().__init__(message, code=-32602)


class PluginExecutionError(PluginException):
    """Raised when query execution fails on the database."""
    def __init__(self, message: str, data: Any | None = None) -> None:
        super().__init__(message, code=-32000, data=data)


@dataclass
class CatalogColumn:
    name: str
    data_type: str
    is_nullable: bool = True
    is_primary_key: bool = False


@dataclass
class CatalogTable:
    name: str
    schema: str = "dbo"
    columns: list[CatalogColumn] = field(default_factory=list)
    indexes: list[str] = field(default_factory=list)


@dataclass
class KnowledgeCatalog:
    schemas: list[str] = field(default_factory=list)
    tables: list[dict[str, Any]] = field(default_factory=list)
    views: list[dict[str, Any]] = field(default_factory=list)
    extra_metadata: dict[str, Any] = field(default_factory=dict)

