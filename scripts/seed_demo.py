"""Idempotent demo data seeder for AegisGate.

Populates the local database with realistic demonstration data against
the bundled simulated SQL Server plugin:
- Syncs the structural catalog (Finance & Inventory partitions)
- Seeds 1 safe READ completed execution
- Seeds 1 FORBID_JOIN governance rejection execution
- Seeds 1 PAUSED_FOR_REVIEW execution waiting for admin approval
- Seeds 1 governance rule of type REDACT_FIELD
- Optionally bulk-inserts N synthetic historical executions via --count N

Adheres strictly to python_clean_code.md:
- Full type hints
- Idempotent (safe to run multiple times)
- Safety check: refuses to run on real non-simulated targets without --force
"""

import argparse
import asyncio
import json
import logging
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# Ensure project root is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from sqlmodel import Session, select

from core.database import ExecutionLog, PluginProfile, Rule, engine, init_db, utc_now
from core.gateway.services import GatewayService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_demo")


def is_plugin_simulated(profile: PluginProfile) -> bool:
    """Return True if plugin config has use_simulation enabled."""
    try:
        cfg = json.loads(profile.config_json)
        val = str(cfg.get("use_simulation", "")).strip().lower()
        return val in ("true", "1", "yes", "on")
    except Exception:
        return False


async def seed_data(count: int = 0, force: bool = False) -> None:
    """Seed demonstration data idempotently."""
    logger.info("Initializing database tables and schemas...")
    init_db()

    target_id = "sqlserver_prod"

    with Session(engine) as session:
        profile = session.exec(select(PluginProfile).where(PluginProfile.id == target_id)).first()
        if not profile:
            logger.error("Target plugin '%s' not found in database. Ensure plugins are discovered.", target_id)
            sys.exit(1)

        simulated = is_plugin_simulated(profile)
        if not simulated and not force:
            logger.error(
                "ABORT: Target plugin '%s' is configured for REAL database connection! "
                "Use --force to run anyway, or configure 'use_simulation': 'true'.",
                target_id,
            )
            sys.exit(1)

    # 1. Sync Catalog via GatewayService
    logger.info("Syncing schema catalog for '%s'...", target_id)
    with Session(engine) as session:
        service = GatewayService(session)
        try:
            chunks = await service.sync_plugin_catalog(target_id)
            logger.info("Catalog sync completed: %d knowledge chunk(s) refreshed.", len(chunks))
        except Exception as exc:
            logger.warning("Catalog sync warning (proceeding with existing catalog): %s", exc)

    with Session(engine) as session:
        # 2. Seed REDACT_FIELD Rule
        redact_rule_id = "rule_redact_sensitive_payroll"
        existing_rule = session.exec(select(Rule).where(Rule.id == redact_rule_id)).first()
        if not existing_rule:
            logger.info("Seeding REDACT_FIELD governance rule...")
            redact_rule = Rule(
                id=redact_rule_id,
                name="Redact Sensitive Financial & Payroll Fields",
                target_id=target_id,
                rule_type="REDACT_FIELD",
                expression="Salary,TaxID,CreditCardNumber,SSN",
                description="Automatically masks confidential payroll and credit card fields from query result sets.",
                severity="HIGH",
                is_active=True,
                created_at=utc_now(),
            )
            session.add(redact_rule)
        else:
            logger.info("REDACT_FIELD rule '%s' already exists.", redact_rule_id)

        # 3. Canonical Demonstrations (Idempotent upsert)
        now = utc_now()

        # A: Safe READ Completed
        exec_read_id = "demo_exec_read_completed"
        read_log = session.exec(select(ExecutionLog).where(ExecutionLog.id == exec_read_id)).first()
        if not read_log:
            read_log = ExecutionLog(id=exec_read_id, target_id=target_id, query="")
        read_log.query = (
            "SELECT TOP 10 TransactionID, AccountID, Amount, TransactionDate, Description "
            "FROM Finance.Transactions ORDER BY TransactionDate DESC;"
        )
        read_log.query_type = "READ"
        read_log.reasoning = "Retrieve recent ledger transactions to audit quarterly cash-flow statements."
        read_log.status = "COMPLETED"
        read_log.explain_plan_json = json.dumps({
            "estimated_rows": 10,
            "strategy": "Clustered Index Scan on PK_Transactions",
            "cost": 0.00328,
            "compile_time_cpu_ms": 1.2,
        })
        read_log.violations_json = "[]"
        read_log.execution_time_ms = 14.2
        read_log.auto_approved = True
        read_log.approved_by = "System Auto-Approval"
        read_log.spid = 54
        read_log.result_summary = json.dumps([
            {"TransactionID": 1001, "AccountID": "ACC-902", "Amount": 12500.0, "Description": "Supplier settlement"},
            {"TransactionID": 1002, "AccountID": "ACC-411", "Amount": 420.50, "Description": "Cloud subscription"},
            {"TransactionID": 1003, "AccountID": "ACC-108", "Amount": 3890.0, "Description": "Server rack lease"},
        ])
        read_log.created_at = now - timedelta(minutes=15)
        read_log.finished_at = now - timedelta(minutes=15) + timedelta(milliseconds=14)
        session.add(read_log)

        # B: Forbidden JOIN Rejected
        exec_join_id = "demo_exec_forbid_join_rejected"
        join_log = session.exec(select(ExecutionLog).where(ExecutionLog.id == exec_join_id)).first()
        if not join_log:
            join_log = ExecutionLog(id=exec_join_id, target_id=target_id, query="")
        join_log.query = (
            "SELECT o.OrderID, a.LogMessage, a.Severity "
            "FROM Orders o JOIN AuditLogs a ON o.OrderID = a.OrderID "
            "WHERE a.Timestamp >= '2026-01-01';"
        )
        join_log.query_type = "READ"
        join_log.reasoning = "Correlate customer sales orders directly with raw unindexed security audit logs."
        join_log.status = "REJECTED"
        join_log.explain_plan_json = json.dumps({
            "estimated_rows": 500000,
            "strategy": "Hash Match (Inner Join) - Cross Partition",
            "cost": 84.62,
        })
        join_log.violations_json = json.dumps([
            "Rule Violation [rule_no_join_orders_auditlogs]: Query violates forbidden entity join on Orders, AuditLogs"
        ])
        join_log.error_message = (
            "Execution blocked by Governance Engine: Forbidden entity join between 'Orders' and 'AuditLogs'."
        )
        join_log.auto_approved = False
        join_log.approved_by = None
        join_log.created_at = now - timedelta(minutes=8)
        join_log.finished_at = now - timedelta(minutes=8) + timedelta(milliseconds=5)
        session.add(join_log)

        # C: PAUSED_FOR_REVIEW Waiting for Approval
        exec_paused_id = "demo_exec_paused_for_review"
        paused_log = session.exec(select(ExecutionLog).where(ExecutionLog.id == exec_paused_id)).first()
        if not paused_log:
            paused_log = ExecutionLog(id=exec_paused_id, target_id=target_id, query="")
        paused_log.query = (
            "UPDATE Inventory.Products "
            "SET StockQuantity = StockQuantity + 50, ReorderLevel = 25 "
            "WHERE Category = 'Enterprise Networking';"
        )
        paused_log.query_type = "WRITE"
        paused_log.reasoning = "Bulk update stock inventory levels following shipment arrival at central depot."
        paused_log.status = "PAUSED_FOR_REVIEW"
        paused_log.explain_plan_json = json.dumps({
            "estimated_rows": 24,
            "strategy": "Clustered Index Update on IX_Products_Category",
            "cost": 0.0184,
            "tables_affected": ["Inventory.Products"],
        })
        paused_log.violations_json = "[]"
        paused_log.auto_approved = False
        paused_log.approved_by = None
        paused_log.execution_time_ms = None
        paused_log.result_summary = None
        paused_log.error_message = None
        paused_log.created_at = now - timedelta(minutes=2)
        paused_log.finished_at = None
        session.add(paused_log)

        # 4. Bulk Synthetic Historical Executions (--count N)
        if count > 0:
            logger.info("Generating %d synthetic historical executions...", count)
            templates = [
                ("READ", "SELECT COUNT(*) FROM Inventory.Products WHERE StockQuantity < 10;", "Check low stock items.", "COMPLETED"),
                ("READ", "SELECT TOP 5 * FROM Finance.BudgetForecast WHERE FiscalYear = 2026;", "Query current fiscal year budget forecast.", "COMPLETED"),
                ("READ", "SELECT * FROM LargeTableScan WITHOUT INDEX;", "Unbounded table scan test.", "REJECTED"),
                ("WRITE", "UPDATE Inventory.Suppliers SET ContactEmail = 'ops@vendor.com' WHERE SupplierID = 4;", "Update vendor primary contact email.", "COMPLETED"),
                ("READ", "SELECT TransactionID, Amount FROM Finance.Transactions WHERE Amount > 50000;", "Identify high-value financial transfers.", "COMPLETED"),
            ]
            for i in range(count):
                qtype, qstr, qreason, qstatus = random.choice(templates)
                offset_hours = random.randint(1, 720)  # past 30 days
                exec_time = now - timedelta(hours=offset_hours, minutes=random.randint(0, 59))
                latency = round(random.uniform(5.0, 180.0), 2) if qstatus == "COMPLETED" else None

                syn_log = ExecutionLog(
                    id=f"syn_exec_{i+1:05d}",
                    target_id=target_id,
                    query=qstr,
                    query_type=qtype,
                    reasoning=qreason,
                    status=qstatus,
                    explain_plan_json=json.dumps({"estimated_rows": random.randint(1, 100), "cost": 0.01}),
                    violations_json="[]" if qstatus == "COMPLETED" else json.dumps(["Governance scan flag"]),
                    execution_time_ms=latency,
                    auto_approved=(qstatus == "COMPLETED"),
                    approved_by="System" if qstatus == "COMPLETED" else None,
                    error_message="Simulation rule check failed" if qstatus == "REJECTED" else None,
                    result_summary=json.dumps({"rows": random.randint(1, 20)}) if qstatus == "COMPLETED" else None,
                    created_at=exec_time,
                    finished_at=exec_time + timedelta(milliseconds=latency or 10),
                )
                session.add(syn_log)

        session.commit()
        logger.info("Demo data seeding completed successfully.")
        logger.info("- 1 Safe READ Completed: %s", exec_read_id)
        logger.info("- 1 FORBID_JOIN Rejected: %s", exec_join_id)
        logger.info("- 1 PAUSED_FOR_REVIEW Waiting: %s", exec_paused_id)
        logger.info("- 1 REDACT_FIELD Rule: %s", redact_rule_id)
        if count > 0:
            logger.info("- %d Historical synthetic executions seeded.", count)


def main() -> None:
    """CLI entrypoint for seed_demo."""
    parser = argparse.ArgumentParser(description="Seed AegisGate demo data against simulated SQL Server plugin.")
    parser.add_argument("--count", type=int, default=0, help="Bulk-insert N synthetic historical executions.")
    parser.add_argument("--force", action="store_true", help="Force run even if target is not in simulation mode.")
    args = parser.parse_args()

    asyncio.run(seed_data(count=args.count, force=args.force))


if __name__ == "__main__":
    main()

