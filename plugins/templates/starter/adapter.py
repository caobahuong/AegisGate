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
from typing import Any, Dict, Optional

# Add SDK root to sys.path if not installed in site-packages
sdk_path = str(Path(__file__).resolve().parent.parent.parent.parent / "sdk")
if sdk_path not in sys.path:
    sys.path.insert(0, sdk_path)

try:
    from aegisgate_sdk import BasePlugin, PluginServer
except ImportError:
    # Direct fallback if run in independent standalone package
    raise ImportError("aegisgate_sdk is required. Run 'pip install aegisgate-sdk' or install from SDK folder.")


class StarterDatabasePlugin(BasePlugin):
    """Reference implementation of a database plugin using AegisGate SDK."""

    def sync_knowledge(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Extract database catalog, schemas, tables, and columns."""
        database_name = config.get("database", "sample_db")
        return {
            "schemas": ["public", "analytics"],
            "tables": [
                {
                    "name": "users",
                    "schema": "public",
                    "columns": [
                        {"name": "id", "type": "INT", "nullable": False, "is_pk": True},
                        {"name": "email", "type": "VARCHAR(255)", "nullable": False},
                        {"name": "created_at", "type": "TIMESTAMP", "nullable": False},
                    ],
                    "indexes": ["PK_users_id", "UQ_users_email"],
                },
                {
                    "name": "transactions",
                    "schema": "analytics",
                    "columns": [
                        {"name": "txn_id", "type": "BIGINT", "nullable": False, "is_pk": True},
                        {"name": "user_id", "type": "INT", "nullable": False},
                        {"name": "amount", "type": "DECIMAL(12,2)", "nullable": False},
                        {"name": "status", "type": "VARCHAR(32)", "nullable": False},
                    ],
                    "indexes": ["PK_transactions_id", "IX_transactions_user_id"],
                },
            ],
            "views": [
                {"name": "active_users_view", "schema": "public"}
            ],
            "database": database_name,
        }

    def dry_run(self, query: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Perform dry-run query inspection and return SHOWPLAN / EXPLAIN plan."""
        normalized = query.strip().upper()
        
        # Simple simulated query plan
        operation = "READ" if normalized.startswith("SELECT") else "WRITE"
        has_cross_join = "CROSS JOIN" in normalized or ("," in normalized and "FROM" in normalized and "JOIN" not in normalized)
        
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
            "explain_plan": explain_plan,
            "risk_score": 75 if has_cross_join else (25 if "WHERE" not in normalized else 5),
            "estimated_rows": 10 if "WHERE" in normalized else 50000,
        }

    def execute(self, query: str, config: Dict[str, Any]) -> Dict[str, Any]:
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

    def abort(self, spid: Optional[int], config: Dict[str, Any]) -> bool:
        """Terminate the active session on target database."""
        # Simulated successful kill of spid
        return True


if __name__ == "__main__":
    PluginServer(StarterDatabasePlugin()).run()

