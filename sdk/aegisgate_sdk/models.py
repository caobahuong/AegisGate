"""AegisGate Plugin SDK - Models and Typed Contracts."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class PluginException(Exception):
    """Base exception for all plugin errors."""
    def __init__(self, message: str, code: int = -32603, data: Optional[Any] = None) -> None:
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
    def __init__(self, message: str, data: Optional[Any] = None) -> None:
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
    columns: List[CatalogColumn] = field(default_factory=list)
    indexes: List[str] = field(default_factory=list)


@dataclass
class KnowledgeCatalog:
    schemas: List[str] = field(default_factory=list)
    tables: List[Dict[str, Any]] = field(default_factory=list)
    views: List[Dict[str, Any]] = field(default_factory=list)
    extra_metadata: Dict[str, Any] = field(default_factory=dict)
