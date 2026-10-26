#!/usr/bin/env python3
"""AegisGate Starter Database Plugin Adapter.

This file demonstrates how to build an external database plugin using the
AegisGate Plugin SDK. Only 4 methods are required to provide full integration:
1. sync_knowledge
2. dry_run
3. execute
4. abort
"""

import sys
from pathlib import Path
from typing import Any

# Add SDK root to sys.path if not installed in site-packages
sdk_path = str(Path(__file__).resolve().parent.parent.parent.parent / "sdk")
if sdk_path not in sys.path:
    sys.path.insert(0, sdk_path)

try:
    from aegisgate_sdk import BasePlugin, PluginServer
except ImportError:
    # Direct fallback if run in independent standalone package
    raise ImportError(
        "aegisgate_sdk is required. Run 'pip install aegisgate-sdk' or install from SDK folder."
    ) from None


class StarterDatabasePlugin(BasePlugin):
    """Reference implementation of a database plugin using AegisGate SDK."""

    def sync_knowledge(self, config: dict[str, Any]) -> dict[str, Any]:
        """Extract database catalog, schemas, tables, and columns."""
        database_name = config.get("database", "sample_db")
        tables = [
            {
                "name": "users",
                "schema_name": "public",
                "columns": [
                    {"name": "id", "data_type": "INT", "is_nullable": False, "is_primary_key": True},
                    {"name": "email", "data_type": "VARCHAR(255)", "is_nullable": False, "is_primary_key": False},
                    {"name": "created_at", "data_type": "TIMESTAMP", "is_nullable": False, "is_primary_key": False},
                ],
                "indexes": [{"name": "PK_users_id", "columns": ["id"], "is_unique": True}],
            },
            {
                "name": "transactions",
                "schema_name": "analytics",
                "columns": [
                    {"name": "txn_id", "data_type": "BIGINT", "is_nullable": False, "is_primary_key": True},
                    {"name": "user_id", "data_type": "INT", "is_nullable": False, "is_primary_key": False},
                    {"name": "amount", "data_type": "DECIMAL(12,2)", "is_nullable": False, "is_primary_key": False},
                    {"name": "status", "data_type": "VARCHAR(32)", "is_nullable": False, "is_primary_key": False},
                ],
                "indexes": [{"name": "PK_transactions_id", "columns": ["txn_id"], "is_unique": True}],
            },
        ]
        return {
            "partitions": [
                {
                    "partition_key": "General",
                    "title": "General Subsystem",
                    "tables": tables,
                }
            ],
            "target_id": str(config.get("target_id") or "starter_plugin"),
            "timestamp": "2026-10-26T00:00:00Z",
            "schemas": ["public", "analytics"],
            "tables": tables,
            "views": [{"name": "active_users_view", "schema": "public"}],
            "database": database_name,
        }

    def dry_run(self, query: str, config: dict[str, Any]) -> dict[str, Any]:
        """Perform dry-run query inspection and return SHOWPLAN / EXPLAIN plan."""
        normalized = query.strip().upper()

        # Simple simulated query plan
        operation = "READ" if normalized.startswith("SELECT") else "WRITE"
        has_cross_join = "CROSS JOIN" in normalized or (
            "," in normalized and "FROM" in normalized and "JOIN" not in normalized
        )

        explain_plan = {
            "Plan": {
                "Node Type": "Index Scan" if "WHERE" in normalized else "Seq Scan",
                "Total Cost": 12.5 if "WHERE" in normalized else 1250.0,
                "Plan Rows": 10 if "WHERE" in normalized else 50000,
                "Relation Name": "users",
                "Strategy": "Index Lookup" if "WHERE" in normalized else "Full Table Scan",
            },
            "QueryType": operation,
        }

        return {
            "is_valid": True,
            "explain_plan": explain_plan,
            "risk_score": 75 if has_cross_join else (25 if "WHERE" not in normalized else 5),
            "estimated_rows": 10 if "WHERE" in normalized else 50000,
        }

    def execute(self, query: str, config: dict[str, Any]) -> dict[str, Any]:
        """Execute the query and return data payload."""
        normalized = query.strip().upper()

        # Return mock data matching query type
        if normalized.startswith("SELECT"):
            return {
                "rows_affected": 2,
                "data": [
                    {"id": 1, "email": "alice@example.com", "status": "active"},
                    {"id": 2, "email": "bob@example.com", "status": "active"},
                ],
                "spid": 101,
            }
        else:
            return {
                "rows_affected": 1,
                "data": [],
                "spid": 101,
            }

    def abort(self, spid: int | None, config: dict[str, Any]) -> bool:
        """Terminate the active session on target database."""
        # Simulated successful kill of spid
        return True


if __name__ == "__main__":
    PluginServer(StarterDatabasePlugin()).run()
