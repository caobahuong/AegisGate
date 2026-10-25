"""AegisGate Plugin SDK - Official SDK for building database plugins."""

from .base import BasePlugin
from .models import (
    CatalogColumn,
    CatalogTable,
    KnowledgeCatalog,
    PluginConfigError,
    PluginException,
    PluginExecutionError,
)
from .server import PluginServer

__all__ = [
    "BasePlugin",
    "CatalogColumn",
    "CatalogTable",
    "KnowledgeCatalog",
    "PluginConfigError",
    "PluginException",
    "PluginExecutionError",
    "PluginServer",
]
__version__ = "1.0.0"
