"""AegisGate Plugin SDK - Base Plugin Interface.

Strictly follows python_clean_code.md:
- 100% Type Hints
- Abstract Base Class defining the 4 core lifecycle methods + ping
- Comprehensive docstrings
"""

from abc import ABC, abstractmethod
from typing import Any


class BasePlugin(ABC):
    """Abstract Base Class for all AegisGate database plugins.
    
    External developers implement this class to build connectors for any database
    (PostgreSQL, Redis, ClickHouse, Snowflake, Oracle, Cassandra, etc.).
    """

    @abstractmethod
    def sync_knowledge(self, config: dict[str, Any]) -> dict[str, Any]:
        """Extract database catalog, schemas, tables, columns, types, and indexes.

        Args:
            config: Database connection configuration parameters.

        Returns:
            Dictionary containing schema metadata:
            {"schemas": [...], "tables": [...], "views": [...]}
        """

    @abstractmethod
    def dry_run(self, query: str, config: dict[str, Any]) -> dict[str, Any]:
        """Perform dry-run inspection and produce execution explain plan without mutating state.

        Args:
            query: The SQL or command statement to inspect.
            config: Database connection configuration parameters.

        Returns:
            Dictionary containing explain plan and risk metrics:
            {"explain_plan": {...}, "risk_score": 0, "operation": "SELECT"}
        """

    @abstractmethod
    def execute(self, query: str, config: dict[str, Any]) -> dict[str, Any]:
        """Execute the query on the target database and return results.

        Args:
            query: The query statement to execute.
            config: Database connection configuration parameters.

        Returns:
            Dictionary containing query results:
            {"rows_affected": int, "data": list[dict], "spid": Optional[int]}
        """

    @abstractmethod
    def abort(self, spid: int | None, config: dict[str, Any]) -> bool:
        """Emergency kill/abort command for a running query or connection.

        Args:
            spid: The database session ID or process ID to terminate.
            config: Database connection configuration parameters.

        Returns:
            True if session was terminated successfully, False otherwise.
        """

    def ping(self, config: dict[str, Any] | None = None) -> dict[str, Any]:
        """Optional health check and handshake method.

        Default implementation returns pong status. Subclasses may override
        to test actual socket connectivity.
        """
        return {"status": "pong", "protocol": "JSON-RPC 2.0", "sdk": "aegisgate-sdk/1.0"}

