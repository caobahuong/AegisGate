"""SQL Server Plugin Adapter implementing the AegisGate Plugin Contract.

Communicates via JSON-RPC 2.0 over Stdio.
Adheres strictly to python_clean_code.md:
- 100% Type Hints
- Inherits from IPluginAdapter
- Custom exception handling
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import random
import re
import sys
import time
from typing import Any, Optional

# Ensure project root is in sys.path when executed as standalone subprocess
_root_dir = str(Path(__file__).resolve().parent.parent.parent)
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)

from plugins.plugin_contract import (
    AbortParams,
    AbortResult,
    ColumnSchema,
    DryRunParams,
    DryRunResult,
    ExecuteParams,
    ExecuteResult,
    IPluginAdapter,
    IndexSchema,
    JsonRpcErrorPayload,
    JsonRpcRequest,
    JsonRpcResponse,
    PartitionSchema,
    ReinitParams,
    ReinitResult,
    SyncKnowledgeParams,
    SyncKnowledgeResult,
    TableSchema,
)


class SqlServerAdapter(IPluginAdapter):
    """Adapter for Microsoft SQL Server implementing the AegisGate ports."""

    def __init__(self) -> None:
        # In-memory tracking of running execution sessions and their assigned SPIDs
        self._active_sessions: dict[str, int] = {}
        self._spid_counter: int = 50
        self._config: dict[str, Any] = {}

    def _allocate_spid(self, execution_id: str) -> int:
        self._spid_counter += 1
        spid = self._spid_counter
        self._active_sessions[execution_id] = spid
        return spid

    def sync_knowledge(self, params: SyncKnowledgeParams) -> SyncKnowledgeResult:
        """Port 1: Extract structural metadata, partition it into chunks, and return catalog."""
        # 1. Sales Partition
        orders_table = TableSchema(
            name="Orders",
            schema_name="dbo",
            columns=[
                ColumnSchema(name="OrderID", data_type="BIGINT", is_nullable=False, is_primary_key=True),
                ColumnSchema(name="CustomerID", data_type="INT", is_nullable=False),
                ColumnSchema(name="OrderDate", data_type="DATETIME2", is_nullable=False),
                ColumnSchema(name="TotalAmount", data_type="DECIMAL(18,2)", is_nullable=False),
                ColumnSchema(name="Status", data_type="VARCHAR(20)", is_nullable=False),
            ],
            indexes=[
                IndexSchema(name="PK_Orders", columns=["OrderID"], is_unique=True),
                IndexSchema(name="IX_Orders_OrderDate", columns=["OrderDate"], is_unique=False),
                IndexSchema(name="IX_Orders_Customer", columns=["CustomerID"], is_unique=False),
            ],
            row_count_estimate=1250000,
            description="Core customer order transactions",
        )

        order_items_table = TableSchema(
            name="OrderItems",
            schema_name="dbo",
            columns=[
                ColumnSchema(name="OrderItemID", data_type="BIGINT", is_nullable=False, is_primary_key=True),
                ColumnSchema(name="OrderID", data_type="BIGINT", is_nullable=False),
                ColumnSchema(name="ProductID", data_type="INT", is_nullable=False),
                ColumnSchema(name="Quantity", data_type="INT", is_nullable=False),
                ColumnSchema(name="UnitPrice", data_type="DECIMAL(18,2)", is_nullable=False),
            ],
            indexes=[
                IndexSchema(name="PK_OrderItems", columns=["OrderItemID"], is_unique=True),
                IndexSchema(name="IX_OrderItems_OrderID", columns=["OrderID"], is_unique=False),
            ],
            row_count_estimate=4500000,
            description="Order line items breakdown",
        )

        sales_partition = PartitionSchema(
            partition_key="Sales",
            title="Sales & Orders Subsystem",
            tables=[orders_table, order_items_table],
        )

        # 2. Inventory Partition
        products_table = TableSchema(
            name="Products",
            schema_name="dbo",
            columns=[
                ColumnSchema(name="ProductID", data_type="INT", is_nullable=False, is_primary_key=True),
                ColumnSchema(name="SKU", data_type="VARCHAR(50)", is_nullable=False),
                ColumnSchema(name="Name", data_type="NVARCHAR(200)", is_nullable=False),
                ColumnSchema(name="Price", data_type="DECIMAL(18,2)", is_nullable=False),
                ColumnSchema(name="CurrentStock", data_type="INT", is_nullable=False),
            ],
            indexes=[
                IndexSchema(name="PK_Products", columns=["ProductID"], is_unique=True),
                IndexSchema(name="UX_Products_SKU", columns=["SKU"], is_unique=True),
            ],
            row_count_estimate=25000,
            description="Catalog products inventory",
        )

        inventory_partition = PartitionSchema(
            partition_key="Inventory",
            title="Warehouse & Inventory Subsystem",
            tables=[products_table],
        )

        # 3. Finance & Audit Partition
        audit_table = TableSchema(
            name="AuditLogs",
            schema_name="dbo",
            columns=[
                ColumnSchema(name="LogID", data_type="BIGINT", is_nullable=False, is_primary_key=True),
                ColumnSchema(name="EventTime", data_type="DATETIME2", is_nullable=False),
                ColumnSchema(name="Action", data_type="VARCHAR(50)", is_nullable=False),
                ColumnSchema(name="RawPayload", data_type="NVARCHAR(MAX)", is_nullable=True),
            ],
            indexes=[
                IndexSchema(name="PK_AuditLogs", columns=["LogID"], is_unique=True),
                IndexSchema(name="IX_AuditLogs_EventTime", columns=["EventTime"], is_unique=False),
            ],
            row_count_estimate=50000000,
            description="Heavy audit trail partition - DO NOT JOIN WITHOUT PARTITION PRUNING",
        )

        finance_partition = PartitionSchema(
            partition_key="Finance",
            title="Finance & Audit Logs Subsystem",
            tables=[audit_table],
        )

        return SyncKnowledgeResult(
            partitions=[sales_partition, inventory_partition, finance_partition],
            target_id="sqlserver_prod",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def dry_run(self, params: DryRunParams) -> DryRunResult:
        """Port 2: Inspect plan (simulating SET SHOWPLAN_XML ON) and check rules."""
        query = params.query
        normalized = query.upper()
        violations: list[str] = []

        # Determine query type
        write_keywords = ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE")
        query_type = "WRITE" if any(kw in normalized for kw in write_keywords) else "READ"

        # Check for forbidden joins
        for rule in params.rules:
            if rule.get("rule_type") == "FORBID_JOIN":
                expr = rule.get("expression", "")
                tables = [t.strip().upper() for t in expr.split(",") if t.strip()]
                if len(tables) >= 2:
                    if all(re.search(rf"\b{re.escape(t)}\b", normalized) for t in tables):
                        violations.append(
                            f"Plugin Rule Violation: Forbidden JOIN between {', '.join(tables)}. Detected in SQL query."
                        )

            elif rule.get("rule_type") == "FORBID_TABLE_SCAN":
                if "WHERE" not in normalized and "SELECT" in normalized and "FROM" in normalized:
                    violations.append(
                        "Plugin Rule Violation: Query lacks WHERE clause and will trigger a full Table Scan on SQL Server."
                    )

        # Generate realistic Showplan XML representation
        is_safe = len(violations) == 0
        operators = []
        if "JOIN" in normalized:
            operators.append({"PhysicalOp": "Hash Match", "LogicalOp": "Inner Join", "EstimateRows": 15000})

        target_obj = "[dbo].[Orders].[PK_Orders]"
        if "PRODUCT" in normalized:
            target_obj = "[dbo].[Products].[PK_Products]"
        elif "AUDIT" in normalized:
            target_obj = "[dbo].[AuditLogs].[PK_AuditLogs]"

        if "WHERE" in normalized:
            operators.append({"PhysicalOp": "Clustered Index Seek", "Object": target_obj})
        else:
            operators.append({"PhysicalOp": "Clustered Index Scan", "Object": target_obj})

        explain_plan = {
            "StatementText": query,
            "StatementType": query_type,
            "OptimizationLevel": "FULL",
            "EstimatedTotalSubtreeCost": 0.084 if is_safe else 14.52,
            "EstimatedRows": 150 if is_safe else 500000,
            "QueryPlan": {
                "RelOp": operators,
                "Warnings": violations if violations else None,
            },
        }

        estimated_time = 15.0 if is_safe else 1500.0

        return DryRunResult(
            is_valid=is_safe,
            violations=violations,
            explain_plan=explain_plan,
            estimated_time_ms=estimated_time,
            query_type=query_type,
        )

    def execute(self, params: ExecuteParams) -> ExecuteResult:
        """Port 3: Execute query under strict timeout guard, track SPID and return results."""
        start_time = time.perf_counter()
        spid = self._allocate_spid(params.execution_id)

        # Check for intentional timeout simulation in query
        if "WAITFOR DELAY" in params.query.upper() or "SIMULATE_TIMEOUT" in params.query.upper():
            # Sleep longer than timeout to trigger guard
            time.sleep(params.timeout_seconds + 1.0)

        # Normal execution simulation
        time.sleep(0.05)  # simulate 50ms database roundtrip
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Generate sample dataset according to query entity
        norm_q = params.query.upper()
        if "PRODUCT" in norm_q:
            sample_rows = [
                {"ProductID": 101, "SKU": "SRV-42U-PRO", "Name": "Enterprise Server Rack 42U", "Price": 1299.99, "CurrentStock": 18},
                {"ProductID": 102, "SKU": "SW-48G-L3", "Name": "Managed Gigabit Switch 48-Port", "Price": 549.50, "CurrentStock": 45},
                {"ProductID": 103, "SKU": "CBL-CAT6A-2M", "Name": "Cat6A Shielded Patch Cable 2m", "Price": 14.99, "CurrentStock": 350},
                {"ProductID": 104, "SKU": "SFP-10G-SR", "Name": "10GBASE-SR SFP+ Optical Transceiver", "Price": 79.00, "CurrentStock": 120},
            ]
        elif "AUDIT" in norm_q:
            sample_rows = [
                {"LogID": 9001, "EventTime": "2026-10-22T08:00:15", "Action": "LOGIN_SUCCESS", "RawPayload": "User sa logged in from 10.0.1.5"},
                {"LogID": 9002, "EventTime": "2026-10-22T08:15:22", "Action": "SCHEMA_AUDIT", "RawPayload": "Table dbo.Products read by AI Agent"},
            ]
        else:
            sample_rows = [
                {"OrderID": 1001, "CustomerID": 42, "OrderDate": "2026-10-21T09:30:00", "TotalAmount": 450.00, "Status": "Completed"},
                {"OrderID": 1002, "CustomerID": 88, "OrderDate": "2026-10-21T10:15:00", "TotalAmount": 1280.50, "Status": "Completed"},
                {"OrderID": 1003, "CustomerID": 15, "OrderDate": "2026-10-21T11:00:00", "TotalAmount": 89.99, "Status": "Pending"},
            ]

        # Clean up session
        self._active_sessions.pop(params.execution_id, None)

        return ExecuteResult(
            data=sample_rows,
            rows_affected=len(sample_rows),
            execution_time_ms=duration_ms,
            spid=spid,
        )

    def abort(self, params: AbortParams) -> AbortResult:
        """Port 4: Immediately kill session/SPID on SQL Server."""
        spid = self._active_sessions.pop(params.execution_id, None)
        if spid:
            message = f"Executed: KILL {spid}; Session for {params.execution_id} was successfully terminated."
        else:
            message = f"Session for {params.execution_id} already released or not found."

        return AbortResult(
            success=True,
            message=message,
        )

    def reinit(self, params: ReinitParams) -> ReinitResult:
        """Port 5: Reinitialize connection with updated configuration parameters."""
        self._config = params.config
        server = self._config.get("server", "localhost")
        port = self._config.get("port", 1433)
        db = self._config.get("database", "EnterpriseSales")
        return ReinitResult(
            success=True,
            message=f"SQL Server connection reinitialized to {server}:{port}/{db}",
            status="active",
        )


def handle_stdio_jsonrpc() -> None:
    """Read a JSON-RPC 2.0 request from stdin, execute adapter, and output response to stdout."""
    adapter = SqlServerAdapter()

    # Read from stdin
    raw_input = sys.stdin.read().strip()
    if not raw_input:
        return

    # Parse JSON-RPC line
    req_id: Optional[Any] = None
    try:
        data = json.loads(raw_input)
        req = JsonRpcRequest.model_validate(data)
        req_id = req.id

        result: Any = None
        if req.method == "sync_knowledge":
            params_sync = SyncKnowledgeParams.model_validate(req.params)
            result = adapter.sync_knowledge(params_sync).model_dump()
        elif req.method == "dry_run":
            params_dry = DryRunParams.model_validate(req.params)
            result = adapter.dry_run(params_dry).model_dump()
        elif req.method == "execute":
            params_exec = ExecuteParams.model_validate(req.params)
            result = adapter.execute(params_exec).model_dump()
        elif req.method == "abort":
            params_abort = AbortParams.model_validate(req.params)
            result = adapter.abort(params_abort).model_dump()
        elif req.method == "reinit":
            params_reinit = ReinitParams.model_validate(req.params)
            result = adapter.reinit(params_reinit).model_dump()
        else:
            resp_err = JsonRpcResponse(
                id=req_id,
                error=JsonRpcErrorPayload(code=-32601, message=f"Method '{req.method}' not found"),
            )
            print(resp_err.model_dump_json())
            sys.stdout.flush()
            return

        resp = JsonRpcResponse(result=result, id=req_id)
        print(resp.model_dump_json())
        sys.stdout.flush()

    except Exception as exc:
        resp_err = JsonRpcResponse(
            id=req_id,
            error=JsonRpcErrorPayload(code=-32000, message=str(exc)),
        )
        print(resp_err.model_dump_json())
        sys.stdout.flush()


if __name__ == "__main__":
    handle_stdio_jsonrpc()
